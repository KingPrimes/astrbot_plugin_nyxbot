"""Market service / 市场服务

封装 Warframe.Market 的业务逻辑。
已拆分:
  - market_sync.py → MarketSyncService (数据同步)
  - market_orders.py → MarketOrdersService (物品匹配 + 订单查询)
  - market_ducats.py → MarketDucatsService (杜卡币)
  - market_riven.py → MarketRivenService (紫卡拍卖)

本文件保留: 赤毒/信条拍卖查询、本地幻纹/武器查询、缓存。
"""
from __future__ import annotations

from tortoise.exceptions import DoesNotExist

from astrbot.api import logger

from ..api import MarketClient
from ..model.ephemeras import Ephemeras
from ..model.lich_sister_weapons import LichSisterWeapons
from ..model.market import (
    LichSisterAuction,
    LichSisterItem,
    LichSisterOwner,
    MarketLichSister,
    MarketLichSisterPayload,
)


class MarketService:
    """市场数据服务（赤毒/信条/缓存）。"""

    # ══════════════════════════════════════════════════════════════════
    # 本地数据库查询
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def get_local_ephemera(cls, name: str) -> Ephemeras | None:
        """按名称精确查询 Ephemeras。"""
        try:
            return await Ephemeras.get(name=name)
        except DoesNotExist:
            return None

    @classmethod
    async def get_local_lich_sister_weapon(
        cls, name: str
    ) -> LichSisterWeapons | None:
        """按名称精确查询 LichSisterWeapons。"""
        try:
            return await LichSisterWeapons.get(name=name)
        except DoesNotExist:
            return None

    # ══════════════════════════════════════════════════════════════════
    # 赤毒/信条拍卖查询 — 镜像 Java MarketLichsSisterUtils
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def search_market_lich_sister(
        cls, keyword: str, search_type: str
    ) -> tuple[str, MarketLichSister | None] | tuple[list[str], None] | None:
        """搜索赤毒/信条拍卖 — 镜像 Java MarketLichsSisterUtils.getAuctions()。

        Args:
            keyword: 武器名称关键词。
            search_type: "lich" 或 "sister"。

        Returns:
            (item_name, MarketLichSister) 或 (possible_items, None) 或 None。
        """
        try:
            weapon = await LichSisterWeapons.get(name=keyword)
        except DoesNotExist:
            weapons = await LichSisterWeapons.filter(
                name__contains=keyword
            ).limit(15).all()
            if weapons:
                weapon = weapons[0]
            else:
                return ([], None)

        slug = weapon.slug
        if not slug:
            return None

        raw_auctions = await cls._call_search_auctions(
            keyword,
            weapon_url_name=slug,
            auction_type=search_type,
            has_ephemera=False,
            sort_by="price_asc",
            damage_min=25,
            damage_max=60,
        )
        if raw_auctions is None:
            return None
        if not raw_auctions:
            return (weapon.name or keyword, MarketLichSister(payload=None))

        # 过滤 + 排序 → 取 top 10
        filtered = cls._filter_and_sort_auctions(raw_auctions)

        auction_list: list[LichSisterAuction] = []
        for a in filtered:
            item_data = a.get("item", {})
            owner = a.get("owner", {})
            element = item_data.get("element")
            if not isinstance(element, (str, type(None))):
                element = str(element)

            auction_list.append(
                LichSisterAuction(
                    buyout_price=a.get("buyout_price"),
                    starting_price=a.get("starting_price"),
                    top_bid=a.get("top_bid"),
                    visible=a.get("visible"),
                    closed=a.get("closed"),
                    platform=a.get("platform"),
                    id=a.get("id"),
                    item=LichSisterItem(
                        type=item_data.get("type"),
                        damage=item_data.get("damage"),
                        weapon_url_name=item_data.get("weapon_url_name"),
                        having_ephemera=item_data.get("having_ephemera"),
                        element=element,
                    ) if item_data else None,
                    owner=LichSisterOwner(
                        reputation=owner.get("reputation"),
                        ingame_name=owner.get("ingame_name"),
                        status=owner.get("status"),
                        id=owner.get("id"),
                    ) if owner else None,
                )
            )

        return (
            weapon.name or keyword,
            MarketLichSister(
                payload=MarketLichSisterPayload(
                    auctions=auction_list,
                    item_name=weapon.name or keyword,
                )
            ),
        )

    # ══════════════════════════════════════════════════════════════════
    # 共享工具 / Shared utilities — 消除 market.py / market_riven.py 重复
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def _filter_and_sort_auctions(
        raw_auctions: list[dict], top_n: int = 10
    ) -> list[dict]:
        """过滤在线卖家 + 按价格排序取 top_n — 消除两处完全相同的三段式过滤。

        market.py search_market_lich_sister 和 market_riven.py search_market_riven
        使用完全相同的 closed/visible/status 过滤和 buyout/starting/top_bid 排序。
        """
        filtered = [
            a
            for a in raw_auctions
            if not a.get("closed")
            and a.get("visible")
            and (a.get("owner") or {}).get("status") in ("online", "ingame")
        ]
        filtered.sort(
            key=lambda a: (
                a.get("buyout_price")
                or a.get("starting_price")
                or a.get("top_bid")
                or 999999
            ),
        )
        return filtered[:top_n]

    @classmethod
    async def _call_search_auctions(
        cls, log_keyword: str, **kwargs: object
    ) -> list[dict] | None:
        """封装 MarketClient.search_auctions 的 try/except + 空检查 + payload 提取。

        消除 market.py 和 market_riven.py 中完全相同的异常处理样板。
        """
        try:
            resp = await MarketClient.search_auctions(**kwargs)
        except Exception:
            logger.exception(f"Market API 查询失败: {log_keyword}")
            return None
        if not resp:
            return None
        return resp.get("payload", {}).get("auctions", [])

    # ══════════════════════════════════════════════════════════════════
    # 缓存
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    def clear_cache(cls) -> None:
        """清除市场数据缓存。"""
        # TODO: 待实现缓存逻辑
