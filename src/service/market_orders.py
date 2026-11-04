"""Market orders service / 市场订单查询服务

OrdersItems 多步匹配管道 + Warframe.Market 订单查询。
镜像 Java: MarketOrderUtils + MarketCommonUtils
"""
from __future__ import annotations

import asyncio

from tortoise.exceptions import DoesNotExist

from astrbot.api import logger

from ..api import MarketClient
from ..api.market import Platform
from ..model.market import MarketUser, Orders, OrderWithUser
from ..model.market_result import MarketResult
from ..model.orders_items import OrdersItems
from .smart_match import Candidates, Hit, Source, resolve


class MarketOrdersService:
    """市场订单查询服务。"""

    # ══════════════════════════════════════════════════════════════════
    # 本地数据库查询
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def get_local_orders_item(cls, slug: str) -> OrdersItems | None:
        """按 slug 精确查询 OrdersItems。"""
        try:
            return await OrdersItems.get(slug=slug)
        except DoesNotExist:
            return None

    # ══════════════════════════════════════════════════════════════════
    # OrdersItems 多步匹配管道 — 镜像 Java MarketOrderUtils.toDataBase()
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def match_orders_item(cls, keyword: str) -> MarketResult:
        """把名称解析成 OrdersItems —— 走统一的 A~G 搜索链路。

        精确 / 别名 / slug / 拼音 / 前缀都由 ``smart_match.resolve()`` 在内存
        索引里完成，不再对本表做 ``LIKE %x%`` 全表扫描；未命中时返回候选名称。

        Returns:
            MarketResult[OrdersItems, None]：`entity` 或 `possible_items`。
        """
        result = await resolve(keyword, Source.ORDERS)
        if isinstance(result, Hit):
            item = await OrdersItems.get_or_none(id=result.entry.ref)
            return MarketResult(entity=item) if item else MarketResult()
        if isinstance(result, Candidates):
            return MarketResult(
                possible_items=[entry.name for entry in result.entries]
            )
        return MarketResult()

    # ══════════════════════════════════════════════════════════════════
    # 市场订单查询 — 镜像 Java MarketOrderUtils.market()
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def _to_api_platform(platform: str) -> Platform:
        """将平台字符串转为 API 的 Platform 枚举。"""
        mapping = {
            "pc": Platform.pc, "ps4": Platform.ps4,
            "xbox": Platform.xbox, "switch": Platform.switch,
        }
        return mapping.get(platform, Platform.pc)

    @classmethod
    async def _enrich_item_details_from_api(
        cls, slug: str, platform_str: str, item_id: str
    ) -> tuple[int | None, int | None]:
        """从 Market API 补充 reqMasteryRank / tradingTax — 镜像 Java toSet()"""
        try:
            plat = cls._to_api_platform(platform_str)
            set_resp = await MarketClient.fetch_items_set(slug, platform=plat)
            if set_resp:
                for i in set_resp.get("data", {}).get("items", []):
                    if i.get("id") == item_id:
                        await cls._backfill_item_details(item_id, i)
                        return i.get("reqMasteryRank"), i.get("tradingTax")
        except Exception:
            logger.warning(f"获取物品详情失败: {slug}")
        return None, None

    @classmethod
    async def _backfill_item_details(cls, item_id: str, detail: dict) -> None:
        """把 item set 接口里的字段回写进 ``ordersitems``。

        这些字段（reqMasteryRank / tradingTax / setRoot / setParts …）只有
        ``/v2/item/{slug}/set`` 才返回，全量同步要 3893 次请求，不现实。
        这里在「用户查到这个物品」时顺手写回，只写一次（之后 WHERE 不命中）。
        """
        i18n = detail.get("i18n") or {}
        localized = i18n.get("zh-hans") or i18n.get("en") or {}
        values: dict[str, object] = {
            "reqMasteryRank": detail.get("reqMasteryRank"),
            "tradingTax": detail.get("tradingTax"),
            "setRoot": detail.get("setRoot"),
            "setParts": detail.get("setParts") or None,
            "quantityInSet": detail.get("quantityInSet"),
            "tradable": detail.get("tradable"),
            "wikiLink": localized.get("wikiLink"),
        }
        values = {key: value for key, value in values.items() if value is not None}
        if not values:
            return
        try:
            await OrdersItems.filter(id=item_id, reqMasteryRank__isnull=True).update(
                **values
            )
        except Exception as exc:  # 回写失败不影响查询
            logger.debug(f"回写物品详情失败 {item_id}: {exc}")

    @classmethod
    async def _fetch_and_filter_market_orders(
        cls,
        slug: str,
        platform_str: str,
        is_by: bool,
        is_max: bool,
        item: OrdersItems,
    ) -> list[OrderWithUser]:
        """获取并过滤市场订单 — 镜像 Java market()"""
        try:
            plat = cls._to_api_platform(platform_str)
            orders_resp = await MarketClient.fetch_items_orders(slug, platform=plat)
        except Exception:
            logger.exception(f"获取订单列表失败: {slug}")
            return []

        if not orders_resp:
            return []

        raw_orders = orders_resp.get("data", [])
        if not raw_orders:
            return []

        item_id = item.id
        max_rank = item.maxRank
        target_type = "buy" if is_by else "sell"

        filtered: list[OrderWithUser] = []
        for o in raw_orders:
            user = o.get("user", {})
            if user.get("status") == "offline":
                continue
            if o.get("itemId") != item_id:
                continue
            if str(o.get("type", "sell")).lower() != target_type:
                continue
            if is_max and max_rank is not None:
                rank = o.get("rank")
                if rank is not None and rank != max_rank:
                    continue
            filtered.append(
                OrderWithUser(
                    id=o.get("id"),
                    type=o.get("type"),
                    platinum=o.get("platinum"),
                    quantity=o.get("quantity"),
                    rank=o.get("rank"),
                    itemId=o.get("itemId"),
                    user=MarketUser(
                        id=user.get("id"),
                        ingameName=user.get("ingameName"),
                        reputation=user.get("reputation"),
                        status=user.get("status"),
                    ) if user else None,
                )
            )

        filtered.sort(key=lambda o: o.platinum or 0, reverse=is_by)
        return filtered[:8]

    @classmethod
    def _build_orders_model_from_item(
        cls,
        item: OrdersItems,
        platform: str,
        is_by: bool,
        is_max: bool,
        order_users: list[OrderWithUser],
        req_mastery_rank: int | None = None,
        trading_tax: int | None = None
    ) -> Orders:
        """从 OrdersItems 模型构建 Orders 渲染模型。"""
        return Orders(
            name=item.name or "",
            form=platform,
            is_by=is_by,
            is_max=is_max,
            ducats=item.ducats or 0,
            tradingTax=trading_tax or item.tradingTax or 0,
            reqMasteryRank=req_mastery_rank or item.reqMasteryRank or 0,
            orders=order_users,
        )

    @classmethod
    async def search_market_orders(
        cls,
        keyword: str,
        platform: str = "pc",
        is_by: bool = False,
        is_max: bool = False,
    ) -> MarketResult:
        """搜索市场订单 — 镜像 Java MarketOrdersPlugin + MarketOrderUtils。

        流程:
          1. 多步匹配 OrdersItems
          2. 若匹配到多个可能物品 → possible_items 有值
          3. 精确匹配 → 从 Market API 获取订单并过滤/排序
          4. 构建 Orders 模型

        Returns:
            MarketResult[OrdersItems, Orders]。
        """
        match_result = await cls.match_orders_item(keyword)

        if match_result.possible_items:
            return match_result

        item = match_result.entity
        if item is None:
            return MarketResult()

        slug = item.slug
        if not slug:
            return MarketResult()

        (req_mr, tax), order_users = await asyncio.gather(
            cls._enrich_item_details_from_api(slug, platform, item.id),
            cls._fetch_and_filter_market_orders(slug, platform, is_by, is_max, item),
        )

        orders = cls._build_orders_model_from_item(
            item, platform, is_by, is_max, order_users, req_mr, tax
        )

        return MarketResult(entity=item, result=orders)
