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

from typing import TYPE_CHECKING

from tortoise.exceptions import DoesNotExist

from astrbot.api import logger

from ..model.ephemeras import Ephemeras
from ..model.lich_sister_weapons import LichSisterWeapons

if TYPE_CHECKING:
    from ..model.market import MarketLichSister


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
        from ..api import MarketClient
        from ..model.market import (
            LichSisterAuction,
            LichSisterItem,
            LichSisterOwner,
            MarketLichSisterPayload,
        )
        from ..model.market import (
            MarketLichSister as MLS,
        )

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

        try:
            resp = await MarketClient.search_auctions(
                weapon_url_name=slug,
                auction_type=search_type,
                has_ephemera=False,
                sort_by="price_asc",
                damage_min=25,
                damage_max=60,
            )
        except Exception:
            logger.exception(f"赤毒/信条拍卖查询失败: {keyword}")
            return None

        if not resp:
            return None

        raw_auctions = resp.get("payload", {}).get("auctions", [])
        if not raw_auctions:
            return (weapon.name or keyword, MLS(payload=None))

        auction_list = []
        for a in raw_auctions:
            if a.get("closed") or not a.get("visible"):
                continue
            owner = a.get("owner", {})
            if owner.get("status") not in ("online", "ingame"):
                continue

            item_data = a.get("item", {})
            element = item_data.get("element")
            if isinstance(element, str) and element:
                pass
            elif element is None:
                element = None
            else:
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

        auction_list.sort(
            key=lambda a: a.buyout_price or a.starting_price or a.top_bid or 999999,
        )
        auction_list = auction_list[:10]

        return (
            weapon.name or keyword,
            MLS(
                payload=MarketLichSisterPayload(
                    auctions=auction_list,
                    item_name=weapon.name or keyword,
                )
            ),
        )

    # ══════════════════════════════════════════════════════════════════
    # 缓存
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    def clear_cache(cls) -> None:
        """清除市场数据缓存。"""
        ...  # TODO: 待实现缓存逻辑
