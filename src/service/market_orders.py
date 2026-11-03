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

        小写化 + 连续空白归一 + "总图"→"蓝图"。

        这里**不能去掉空格**：名字本身就带空格（``Ember Prime 一套``），
        去掉后 ``name = ?`` 的精确匹配永远命中不了，只能一路退化到模糊/正则。
        去空格的比较由 ``_execute_space_normalized_*`` 在 SQL 里
        ``REPLACE(name, ' ', '')`` 完成。
        """
        return " ".join(keyword.lower().split()).replace("总图", "蓝图")

    @classmethod
    async def _match_orders_item_by_exact_name(
        cls, keyword: str
    ) -> OrdersItems | None:
        """按名称精确匹配 — 镜像 Java findByName()"""
        return await OrdersItems.filter(name__iexact=keyword).first()

    @classmethod
    async def _execute_space_normalized_like(
        cls, like_pattern: str, limit: int = 0
    ) -> list[OrdersItems]:
        """按给定 LIKE 模式做空格归一化查询 — 镜像 Java REPLACE(NAME, ' ', '')

        通配符由调用方负责：包含匹配传 ``%keyword%``，前缀锚定匹配传
        ``prefix%end%``。

        注意不要在这里统一再套一层 ``%...%``：那会把锚定模式退化成
        「首尾字符出现在名字任意位置」，``braton`` 就会命中
        ``Ember Prime 一套``。

        Args:
            like_pattern: 已带通配符的 LIKE 模式（大小写不敏感）。
            limit: 返回条数上限，0 表示不限。

        Returns:
            命中的物品列表，套装（slug 以 set 结尾）排在前面。
        """
        sql = (
            "SELECT * FROM ordersitems "
            "WHERE UPPER(REPLACE(name, ' ', '')) "
            "LIKE UPPER(REPLACE(?, ' ', '')) "
            "ORDER BY CASE WHEN slug LIKE '%set' THEN 0 ELSE 1 END"
        )
        if limit > 0:
            sql += f" LIMIT {int(limit)}"

        try:
            conn = Tortoise.get_connection("default")
            rows = await conn.execute_query_dict(sql, [like_pattern])
        except Exception:
            logger.warning("空格归一化查询失败，回退到空结果")
            return []

        return [OrdersItems(**row) for row in rows]

    @classmethod
    async def _execute_space_normalized_query(
        cls, keyword: str, limit: int = 0
    ) -> list[OrdersItems]:
        """空格归一化包含查询 — ``name LIKE %keyword%``。"""
        return await cls._execute_space_normalized_like(f"%{keyword}%", limit)

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

        模式与 Java 一致，都是**前缀锚定**的 ``^header.*?end.*?``：
        ``embp`` → ``e%p%p%`` 命中 "Ember Prime 一套"；
        ``volt`` → ``vol%t%`` 命中 "Volt Prime 一套"。

        命中后再校验前缀重合度，避免「首尾字符对上、中间无关」的误命中：
        ``braton``（库里没有该物品）不会因为以 b 开头、含 n 就落成
        ``Banshee Prime 一套``，而是继续走候选列表。
        """
        # 名字里的空格在 SQL 里已经被 REPLACE 掉，模式也按无空格构造
        compact = keyword.replace(" ", "")
        if len(compact) < 2:
            return None

        end = compact[-1]
        patterns: list[str] = []
        if "p" in compact and end != "p":
            patterns.append(f"{compact[0]}%p%{end}%")

        # 前缀长度 4 → 1 逐级放宽
        max_prefix_len = min(4, len(compact) - 1)
        for prefix_len in range(max_prefix_len, 0, -1):
            patterns.append(f"{compact[:prefix_len]}%{end}%")

        for pattern in patterns:
            items = await cls._execute_space_normalized_like(pattern, limit=15)
            for item in items:
                if cls._has_matching_prefix(compact, item.name or ""):
                    return item

        return None

    @staticmethod
    def _has_matching_prefix(keyword: str, name: str) -> bool:
        """关键词与候选名至少要重合 3 个起始字符。

        前缀长度 1~2 的 LIKE 模式几乎能命中任何同首字母的物品，``braton``
        （库里没有该物品）就是这样落成 ``Banshee Prime 一套`` 的。要求 3 个
        字符后，``embp``→``Ember Prime``、``volt``→``Volt Prime`` 仍正常，
        而只共享首字母的误命中会被拒掉、转为候选列表。

        关键词不足 4 个字符时不设限，保留 ``bp``、``nyx`` 这类短缩写能力。

        Args:
            keyword: 已去空格的关键词。
            name: 候选物品名（可能含空格）。
        """
        if len(keyword) < 4:
            return True
        target = name.lower().replace(" ", "")
        return target.startswith(keyword[:3])

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
