"""Market orders service / 市场订单查询服务

OrdersItems 多步匹配管道 + Warframe.Market 订单查询。
镜像 Java: MarketOrderUtils + MarketCommonUtils
"""
from __future__ import annotations

import asyncio

from tortoise import Tortoise
from tortoise.exceptions import DoesNotExist

from astrbot.api import logger

from ..api import MarketClient
from ..api.market import Platform
from ..model.market import MarketUser, Orders, OrderWithUser
from ..model.market_result import MarketResult
from ..model.orders_items import OrdersItems
from ..util.alias_cache import AliasCacheHelper


class MarketOrdersService:
    """市场订单查询服务。"""

    _alias_helper = AliasCacheHelper()

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

    @staticmethod
    def _normalize_keyword(keyword: str) -> str:
        """标准化关键词 — 镜像 Java MarketCommonUtils.normalizeInput()

        小写化 + 去空格 + "总图"→"蓝图"。
        """
        return keyword.strip().lower().replace(" ", "").replace("总图", "蓝图")

    @classmethod
    async def _match_orders_item_by_exact_name(
        cls, keyword: str
    ) -> OrdersItems | None:
        """按名称精确匹配 — 镜像 Java findByName()"""
        return await OrdersItems.filter(name__iexact=keyword).first()

    @classmethod
    async def _execute_space_normalized_query(
        cls, keyword: str, limit: int = 0
    ) -> list[OrdersItems]:
        """空格归一化原生 SQL 查询 — 镜像 Java REPLACE(NAME, ' ', '')

        去除 DB 列和关键词中的空格后再进行 LIKE 比较，
        优先返回 slug 以 'set' 结尾的套装物品（镜像 Java SLUG regexp '(.*set)?'）。
        """
        sql = (
            "SELECT * FROM ordersitems "
            "WHERE UPPER(REPLACE(name, ' ', '')) "
            "LIKE UPPER(REPLACE('%' || ? || '%', ' ', '')) "
            "ORDER BY CASE WHEN slug LIKE '%set' THEN 0 ELSE 1 END"
        )
        if limit > 0:
            sql += f" LIMIT {int(limit)}"

        try:
            conn = Tortoise.get_connection("default")
            rows = await conn.execute_query_dict(sql, [keyword])
        except Exception:
            logger.warning("空格归一化查询失败，回退到空结果")
            return []

        return [OrdersItems(**row) for row in rows]

    @classmethod
    async def _replace_aliases_in_keyword(cls, keyword: str) -> str:
        """将关键词中的中文别名替换为英文 — 镜像 Java processAliases()

        使用 AliasCacheHelper 封装缓存 + 预编译正则替换。
        """
        return await cls._alias_helper.replace(keyword)

    @staticmethod
    def _process_prime_in_keyword(keyword: str) -> str:
        """替换简写 "p" 为 "Prime" — 镜像 Java processPrimeKeyword()

        仅在关键词不含 "prime" 但含 "p" 时替换。
        """
        if "prime" not in keyword and "p" in keyword:
            return keyword.replace("p", "Prime")
        return keyword

    @classmethod
    async def _match_orders_item_by_fuzzy_name(
        cls, keyword: str
    ) -> OrdersItems | None:
        """模糊名称匹配 — 镜像 Java findByItemNameLike()

        ORM icontains 快路径命中 set 物品时直接返回；
        未命中或命中非 set 物品时走空格归一化慢路径（优先返回 set 物品）。
        """
        item = await OrdersItems.filter(name__icontains=keyword).first()
        if item and (item.slug or "").endswith("set"):
            return item

        items = await cls._execute_space_normalized_query(keyword, limit=1)
        if items:
            return items[0]
        return item

    @classmethod
    async def _match_orders_item_by_regex_pattern(
        cls, keyword: str
    ) -> OrdersItems | None:
        """首尾 LIKE 匹配 — 镜像 Java tryRegexNameMatch() + findByNameRegex()

        例如 keyword="embp" → LIKE 模式 "emb%p%" → 可匹配 "Ember Prime"
        """
        if len(keyword) < 2:
            return None

        end = keyword[-1]

        if "p" in keyword and not keyword.endswith("p"):
            like_pattern = f"{keyword[0]}%{end}%"
            items = await cls._execute_space_normalized_query(like_pattern, limit=1)
            if items:
                return items[0]

        max_prefix_len = min(4, len(keyword) - 1)
        for prefix_len in range(max_prefix_len, 0, -1):
            header = keyword[:prefix_len]
            like_pattern = f"{header}%{end}%"
            items = await cls._execute_space_normalized_query(like_pattern, limit=1)
            if items:
                return items[0]

        return None

    @classmethod
    async def _find_possible_order_item_names(
        cls, keyword: str
    ) -> list[str]:
        """获取候选物品名称列表 — 镜像 Java getPossibleItems()

        两段式查询:
          1. 用首字符模糊匹配
          2. 若结果为空，用"去掉尾字符"的关键词二次查询
        返回最多 15 条去重名称。
        """
        if not keyword:
            return []

        items: list[OrdersItems] = []

        first_char = keyword[0]
        orm_items = await OrdersItems.filter(
            name__icontains=first_char
        ).limit(15).all()
        items.extend(orm_items)

        if len(items) < 5:
            extra = await cls._execute_space_normalized_query(first_char, limit=15)
            seen = {i.id for i in items}
            for i in extra:
                if i.id not in seen:
                    items.append(i)
                    seen.add(i.id)

        if not items and len(keyword) > 1:
            fallback = keyword[:-1]
            items = await cls._execute_space_normalized_query(fallback, limit=15)

        items = items[:15]
        return list(dict.fromkeys(i.name for i in items if i.name))

    @classmethod
    async def match_orders_item(cls, keyword: str) -> MarketResult:
        """多步匹配 OrdersItems — 镜像 Java MarketOrderUtils.toDataBase()

        匹配优先级:
          1. 精确名称匹配
          2. 别名替换后模糊匹配
          3. Prime 关键词处理后模糊匹配
          4. 首尾正则匹配
          5. 回退：候选名称列表

        Returns:
            MarketResult[OrdersItems, None]。
        """
        kw = cls._normalize_keyword(keyword)

        item = await cls._match_orders_item_by_exact_name(kw)
        if item:
            return MarketResult(entity=item)

        aliased = await cls._replace_aliases_in_keyword(kw)
        if aliased != kw:
            item = await cls._match_orders_item_by_fuzzy_name(aliased)
            if item:
                return MarketResult(entity=item)

        primed = cls._process_prime_in_keyword(aliased)
        if primed != aliased:
            item = await cls._match_orders_item_by_fuzzy_name(primed)
            if item:
                return MarketResult(entity=item)

        item = await cls._match_orders_item_by_regex_pattern(primed)
        if item:
            return MarketResult(entity=item)

        possible = await cls._find_possible_order_item_names(primed)
        return MarketResult(possible_items=possible)

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
                        return i.get("reqMasteryRank"), i.get("tradingTax")
        except Exception:
            logger.warning(f"获取物品详情失败: {slug}")
        return None, None

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
