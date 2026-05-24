"""Market service / 市场服务

封装 Warframe.Market 的业务逻辑以及本地市场数据查询和数据同步。
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from tortoise.exceptions import DoesNotExist

from astrbot.api import logger

from ..api import MarketClient
from ..model.ephemeras import Ephemeras
from ..model.lich_sister_weapons import LichSisterWeapons
from ..model.orders_items import OrdersItems

if TYPE_CHECKING:
    from ..model.market import (
        DucatItem,
        Ducats,
        MarketLichSister,
        MarketRiven,
        MarketRivenPayload,
        Orders,
        RivenAttribute,
        RivenAuction,
        RivenItem,
        RivenOwner,
    )


class MarketService:
    """市场数据服务。"""

    # ══════════════════════════════════════════════════════════════════
    # 数据同步（原 data_sources_init.py）
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def _extract_i18n(item: dict, lang: str = "zh-hans") -> dict:
        """从 API 返回的 item 中提取 i18n 本地化 name/icon/thumb。

        所有 Market API 端点返回的 item 都遵循统一结构:
            item["i18n"][lang] = {"name": "...", "icon": "...", "thumb": "..."}

        Args:
            item: API 返回的原始 item 字典。
            lang: 目标语言代码，默认 "zh-hans"。

        Returns:
            包含 name/icon/thumb 的 dict，缺失时值为 None。
        """
        i18n = item.get("i18n", {})
        localized = i18n.get(lang, {})
        return {
            "name": localized.get("name"),
            "icon": localized.get("icon"),
            "thumb": localized.get("thumb"),
        }

    @classmethod
    async def sync_orders_items(cls) -> None:
        """初始化 OrdersItems（市场订单物品）表数据 — 从 Market API。

        从 /items 端点获取所有可交易物品列表，提取基础字段并通过
        batch_upsert 进行对比插入。
        注意：ducats/vaulted/tradingTax 等字段在 /items 端点中不可用。
        """
        from ..init.engine import get_engine
        from .data_sync import DataSyncService

        logger.info("从 Market API 加载物品数据...")
        await get_engine()

        resp = await MarketClient.fetch_items()
        if not resp:
            logger.warning("物品数据为空，跳过初始化")
            return

        data: list[dict] = resp.get("data", [])
        if not data:
            logger.warning("物品数据为空，跳过")
            return

        items: list[dict] = []
        for item in data:
            items.append({**item, **cls._extract_i18n(item)})

        total_upserted = await DataSyncService.batch_upsert(
            model_cls=OrdersItems,
            items=items,
            key_field="id",
            build_instance=lambda item: OrdersItems(
                id=item["id"],
                slug=item.get("slug"),
                gameRef=item.get("gameRef"),
                maxRank=item.get("maxRank"),
                name=item.get("name"),
                icon=item.get("icon"),
                thumb=item.get("thumb"),
                bulkTradable=item.get("bulkTradable"),
                ducats=item.get("ducats"),
                vaulted=item.get("vaulted"),
                maxAmberStars=item.get("maxAmberStars"),
                maxCyanStars=item.get("maxCyanStars"),
                baseEndo=item.get("baseEndo"),
            ),
            update_fields=[
                "slug", "gameRef", "maxRank", "name", "icon",
                "thumb", "bulkTradable", "ducats", "vaulted",
                "maxAmberStars", "maxCyanStars", "baseEndo",
            ],
        )
        total = await OrdersItems.all().count()
        logger.info(f"物品数据初始化完成，共 {total} 条记录（本次处理 {total_upserted} 条）")

    @classmethod
    async def sync_ephemeras(cls) -> None:
        """初始化 Ephemeras（幻纹）表数据 — 从 Market API。

        从 /lich/ephemeras 和 /sister/ephemeras 两个端点并发获取数据，
        合并后统一 batch_upsert。
        """
        from ..init.engine import get_engine
        from .data_sync import DataSyncService

        logger.info("从 Market API 加载幻纹数据...")
        await get_engine()

        # 并发获取赤毒幻纹 + 信条幻纹（互不依赖）
        lich_resp, sister_resp = await asyncio.gather(
            MarketClient.fetch_lich_ephemeras(),
            MarketClient.fetch_sister_ephemeras(),
        )

        all_data: list[dict] = []

        if lich_resp:
            lich_data = lich_resp.get("data", [])
            for item in lich_data:
                all_data.append({**item, **cls._extract_i18n(item)})
            logger.info(f"赤毒幻纹: {len(lich_data)} 条")
        else:
            logger.warning("赤毒幻纹数据为空")

        if sister_resp:
            sister_data = sister_resp.get("data", [])
            for item in sister_data:
                all_data.append({**item, **cls._extract_i18n(item)})
            logger.info(f"信条幻纹: {len(sister_data)} 条")
        else:
            logger.warning("信条幻纹数据为空")

        if not all_data:
            logger.warning("无幻纹数据可插入")
            return

        total_upserted = await DataSyncService.batch_upsert(
            model_cls=Ephemeras,
            items=all_data,
            key_field="id",
            build_instance=lambda item: Ephemeras(
                id=item["id"],
                slug=item.get("slug"),
                gameRef=item.get("gameRef"),
                animation=item.get("animation"),
                element=item.get("element"),
                name=item.get("name"),
                icon=item.get("icon"),
                thumb=item.get("thumb"),
            ),
            update_fields=["slug", "gameRef", "animation", "element", "name", "icon", "thumb"],
        )
        total = await Ephemeras.all().count()
        logger.info(f"幻纹数据初始化完成，共 {total} 条记录（本次处理 {total_upserted} 条）")

    @classmethod
    async def sync_lich_sister_weapons(cls) -> None:
        """初始化 LichSisterWeapons（信条/赤毒武器）表数据 — 从 Market API。

        从 /lich/weapons 和 /sister/weapons 两个端点并发获取数据，
        合并后统一 batch_upsert。
        """
        from ..init.engine import get_engine
        from .data_sync import DataSyncService

        logger.info("从 Market API 加载信条/赤毒武器数据...")
        await get_engine()

        # 并发获取赤毒武器 + 信条武器（互不依赖）
        lich_resp, sister_resp = await asyncio.gather(
            MarketClient.fetch_lich_weapons(),
            MarketClient.fetch_sister_weapons(),
        )

        all_data: list[dict] = []

        if lich_resp:
            lich_data = lich_resp.get("data", [])
            for item in lich_data:
                all_data.append({**item, **cls._extract_i18n(item)})
            logger.info(f"赤毒武器: {len(lich_data)} 条")
        else:
            logger.warning("赤毒武器数据为空")

        if sister_resp:
            sister_data = sister_resp.get("data", [])
            for item in sister_data:
                all_data.append({**item, **cls._extract_i18n(item)})
            logger.info(f"信条武器: {len(sister_data)} 条")
        else:
            logger.warning("信条武器数据为空")

        if not all_data:
            logger.warning("无信条/赤毒武器数据可插入")
            return

        total_upserted = await DataSyncService.batch_upsert(
            model_cls=LichSisterWeapons,
            items=all_data,
            key_field="id",
            build_instance=lambda item: LichSisterWeapons(
                id=item["id"],
                slug=item.get("slug"),
                icon=item.get("icon"),
                gameRef=item.get("gameRef"),
                reqMasteryRank=item.get("reqMasteryRank"),
                name=item.get("name"),
                thumb=item.get("thumb"),
            ),
            update_fields=["slug", "icon", "gameRef", "reqMasteryRank", "name", "thumb"],
        )
        total = await LichSisterWeapons.all().count()
        logger.info(f"信条/赤毒武器数据初始化完成，共 {total} 条记录（本次处理 {total_upserted} 条）")

    # ══════════════════════════════════════════════════════════════════
    # 远程 API（原有，保持不变）
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def search_items(cls, query: str) -> list[dict] | None:
        """远程搜索物品。

        Args:
            query: 搜索关键词。

        Returns:
            匹配的物品列表。
        """
        ...  # TODO: 由 API 层实现

    @classmethod
    async def get_item_orders(cls, url_name: str) -> dict | None:
        """获取指定物品的订单。

        Args:
            url_name: 物品的 url_name。

        Returns:
            包含订单数据的字典。
        """
        ...  # TODO: 由 API 层实现

    @classmethod
    async def get_lich_weapons(cls) -> list[dict] | None:
        """获取赤毒武器列表（远程）。"""
        ...  # TODO: 由 API 层实现

    @classmethod
    async def get_sister_weapons(cls) -> list[dict] | None:
        """获取信条武器列表（远程）。"""
        ...  # TODO: 由 API 层实现

    @classmethod
    async def search_auctions(
        cls,
        weapon_url_name: str,
        sort_by: str = "price_asc",
        page: int = 0,
    ) -> dict | None:
        """搜索紫卡拍卖。

        Args:
            weapon_url_name: 武器 url_name。
            sort_by: 排序方式。
            page: 页码。

        Returns:
            拍卖搜索结果。
        """
        ...  # TODO: 由 API 层实现

    # ══════════════════════════════════════════════════════════════════
    # 本地数据库查询（原有，保持不变）
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def get_local_orders_item(
        cls, slug: str
    ) -> dict | None:
        """从本地 OrdersItems 表查询物品信息。

        Args:
            slug: URL slug。

        Returns:
            物品信息的字典。
        """
        try:
            item = await OrdersItems.get(slug=slug)
            return {
                "id": item.id,
                "slug": item.slug,
                "gameRef": item.gameRef,
                "maxRank": item.maxRank,
                "name": item.name,
                "icon": item.icon,
                "thumb": item.thumb,
                "bulkTradable": item.bulkTradable,
                "ducats": item.ducats,
                "vaulted": item.vaulted,
                "maxAmberStars": item.maxAmberStars,
                "maxCyanStars": item.maxCyanStars,
                "baseEndo": item.baseEndo,
            }
        except DoesNotExist:
            return None

    @classmethod
    async def search_local_orders_items(
        cls, keyword: str, page: int = 1, page_size: int = 20
    ):
        """从本地 OrdersItems 表模糊搜索物品。

        Returns:
            (记录列表, 总数) 的元组。
        """
        offset = (page - 1) * page_size
        qs = OrdersItems.filter(name__contains=keyword)
        total = await qs.count()
        items = await qs.offset(offset).limit(page_size)
        return list(items), total

    @classmethod
    async def get_local_ephemera(cls, name: str) -> dict | None:
        """从本地 Ephemeras 表查询幻纹信息。"""
        try:
            item = await Ephemeras.get(name=name)
            return {
                "id": item.id,
                "slug": item.slug,
                "gameRef": item.gameRef,
                "animation": item.animation,
                "element": item.element,
                "name": item.name,
                "icon": item.icon,
                "thumb": item.thumb,
            }
        except DoesNotExist:
            return None

    @classmethod
    async def get_local_lich_sister_weapon(cls, name: str) -> dict | None:
        """从本地 LichSisterWeapons 表查询武器信息。"""
        try:
            item = await LichSisterWeapons.get(name=name)
            return {
                "id": item.id,
                "slug": item.slug,
                "icon": item.icon,
                "gameRef": item.gameRef,
                "reqMasteryRank": item.reqMasteryRank,
                "name": item.name,
                "thumb": item.thumb,
            }
        except DoesNotExist:
            return None

    # ══════════════════════════════════════════════════════════════════
    # 杜卡币查询 — 镜像 Java MarketDucatsUtils
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def get_ducats_data(cls) -> Ducats | None:
        """获取杜卡币原始数据 — 镜像 Java getDucats()。

        Returns:
            Ducats 模型实例，失败时返回 None。
        """
        from ..api.api import WF_MARKET_DUCATS
        from ..model.market import Ducats
        from ..util import fetch_json

        try:
            resp = await fetch_json(WF_MARKET_DUCATS, cache_key="market_ducats", ttl=120)
        except Exception:
            logger.warning("获取 Ducats 数据失败")
            return None

        if not resp:
            return None
        try:
            return Ducats(**resp)
        except Exception as e:
            logger.warning(f"解析 Ducats 数据失败: {e}")
            return None

    @classmethod
    def _get_gold_dump(cls, items: list[DucatItem]) -> list[DucatItem]:
        """筛选金垃圾 — 镜像 Java getGodDump(): ducats == 100"""
        return sorted(
            [d for d in items if d.ducats is not None and d.ducats == 100],
            key=lambda d: d.ducats_per_platinum_wa or 0,
            reverse=True,
        )[:10]

    @classmethod
    def _get_silver_dump(cls, items: list[DucatItem]) -> list[DucatItem]:
        """筛选银垃圾 — 镜像 Java getSilverDump(): 45 <= ducats < 100"""
        return sorted(
            [d for d in items if d.ducats is not None and 45 <= d.ducats < 100],
            key=lambda d: d.ducats_per_platinum_wa or 0,
            reverse=True,
        )[:10]

    @classmethod
    def _resolve_ducat_item_names(cls, items: list[DucatItem]) -> None:
        """从本地 OrdersItems 表解析物品名称 — 镜像 Java peek(d -> d.setItem(...))"""
        for d in items:
            if not d.item:
                continue
            try:
                import asyncio
                asyncio.get_event_loop()
            except RuntimeError:
                d.item_name = d.item
                continue
            # 同步查询（DucatItem 的 item 字段是物品 ID 字符串）
            d.item_name = d.item

    @classmethod
    async def get_gold_dump(cls) -> tuple[list[DucatItem], list[DucatItem]]:
        """获取金垃圾数据 — 返回 (day_items, hour_items)。

        镜像 Java getDuats(DucatsType.GOD, ducats)
        """
        ducats = await cls.get_ducats_data()
        if ducats is None or ducats.payload is None:
            return [], []

        day_items = cls._get_gold_dump(ducats.payload.previous_day)
        hour_items = cls._get_gold_dump(ducats.payload.previous_hour)
        cls._resolve_ducat_item_names(day_items)
        cls._resolve_ducat_item_names(hour_items)
        return day_items, hour_items

    @classmethod
    async def get_silver_dump(cls) -> tuple[list[DucatItem], list[DucatItem]]:
        """获取银垃圾数据 — 返回 (day_items, hour_items)。

        镜像 Java getDuats(DucatsType.SILVER, ducats)
        """
        ducats = await cls.get_ducats_data()
        if ducats is None or ducats.payload is None:
            return [], []

        day_items = cls._get_silver_dump(ducats.payload.previous_day)
        hour_items = cls._get_silver_dump(ducats.payload.previous_hour)
        cls._resolve_ducat_item_names(day_items)
        cls._resolve_ducat_item_names(hour_items)
        return day_items, hour_items

    # ══════════════════════════════════════════════════════════════════
    # 市场订单查询 — 镜像 Java MarketOrderUtils
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def search_market_orders(
        cls,
        keyword: str,
        platform: str = "pc",
        is_by: bool = False,
        is_max: bool = False,
    ) -> Orders | tuple[list[str], None] | None:
        """搜索市场订单 — 镜像 Java MarketOrdersPlugin + MarketOrderUtils。

        流程:
          1. 本地 DB 搜索物品
          2. 若匹配到多个可能物品 → 返回 possible_items 列表
          3. 精确匹配 → 从 Market API 获取订单数据
          4. 过滤离线/排序/限制数量 → 构建 Orders 模型

        Args:
            keyword: 物品关键词。
            platform: 平台（pc/ps4/xbox/switch）。
            is_by: True=购买, False=出售。
            is_max: True=仅满级物品。

        Returns:
            Orders 模型、(possible_items, None) 或 None。
        """
        from ..api.market import Platform as ApiPlatform
        from ..model.market import Orders as OrdersModel

        plat_enum = {
            "pc": ApiPlatform.pc, "ps4": ApiPlatform.ps4,
            "xbox": ApiPlatform.xbox, "switch": ApiPlatform.switch,
        }.get(platform, ApiPlatform.pc)

        # 1. 本地查找物品
        item = await cls.get_local_orders_item(keyword)
        if item is None:
            items, total = await cls.search_local_orders_items(keyword, page=1, page_size=15)
            if items:
                names = [i.name for i in items if i.name]
                return (names, None)
            return None

        slug = item.get("slug")
        if not slug:
            return None

        # 2. 获取物品详情（补充段位/交易税等字段）
        try:
            set_resp = await MarketClient.fetch_items_set(slug, platform=plat_enum)
            if set_resp:
                items_node = set_resp.get("data", {}).get("items", [])
                for i in items_node:
                    if i.get("id") == item["id"]:
                        item["reqMasteryRank"] = i.get("reqMasteryRank")
                        item["tradingTax"] = i.get("tradingTax")
                        break
        except Exception:
            logger.warning(f"获取物品详情失败: {slug}")

        # 3. 获取订单列表
        try:
            orders_resp = await MarketClient.fetch_items_orders(slug, platform=plat_enum)
        except Exception:
            logger.exception(f"获取订单列表失败: {slug}")
            return None

        if not orders_resp:
            return None

        raw_orders = orders_resp.get("data", [])
        if not raw_orders:
            return None

        # 4. 过滤和排序
        item_id = item["id"]
        max_rank = item.get("maxRank")
        filtered: list[dict] = []
        for o in raw_orders:
            user = o.get("user", {})
            if user.get("status") == "offline":
                continue
            if o.get("itemId") != item_id:
                continue
            o_type = str(o.get("type", "sell")).lower()
            if is_by and o_type != "buy":
                continue
            if not is_by and o_type != "sell":
                continue
            if is_max and max_rank is not None:
                rank = o.get("rank")
                if rank is not None and rank != max_rank:
                    continue
            filtered.append(o)

        filtered.sort(
            key=lambda o: o.get("platinum") or 0,
            reverse=is_by,
        )
        filtered = filtered[:8]

        # 5. 构建 Orders 模型
        order_users = []
        for o in filtered:
            from ..model.market import MarketUser, OrderWithUser
            user = o.get("user", {})
            ou = OrderWithUser(
                id=o.get("id"),
                type=o.get("type"),
                platinum=o.get("platinum"),
                quantity=o.get("quantity"),
                rank=o.get("rank"),
                item_id=o.get("itemId"),
                user=MarketUser(
                    id=user.get("id"),
                    ingame_name=user.get("ingameName"),
                    reputation=user.get("reputation"),
                    status=user.get("status"),
                ) if user else None,
            )
            order_users.append(ou)

        return OrdersModel(
            name=item.get("name", keyword),
            form=platform,
            is_by=is_by,
            is_max=is_max,
            ducats=item.get("ducats") or 0,
            trading_tax=item.get("tradingTax") or item.get("trading_tax") or 0,
            req_mastery_rank=item.get("reqMasteryRank") or 0,
            orders=order_users,
        )

    # ══════════════════════════════════════════════════════════════════
    # 紫卡市场查询 — 镜像 Java MarketRivenUtils
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def search_market_riven(cls, keyword: str) -> MarketRiven | None:
        """搜索紫卡拍卖 — 镜像 Java MarketRivenUtils.marketRivenParameter()。

        Args:
            keyword: 武器名称关键词。

        Returns:
            MarketRiven 模型或 None。
        """
        from ..model.market import MarketRiven as MR

        # 1. 查找紫卡武器
        from ..model.riven_items import RivenItems
        try:
            riven_item = await RivenItems.get(name=keyword)
        except DoesNotExist:
            items = await RivenItems.filter(name__contains=keyword).limit(10).all()
            if items:
                riven_item = items[0]
            else:
                return None

        # 2. 请求 API
        try:
            resp = await MarketClient.search_auctions(
                weapon_url_name=riven_item.slug or keyword,
                sort_by="price_asc",
                page=0,
            )
        except Exception:
            logger.exception(f"紫卡拍卖查询失败: {keyword}")
            return None

        if not resp:
            return None

        # 3. 解析为 MarketRiven 模型
        try:
            payload = resp.get("payload", {})
            raw_auctions = payload.get("auctions", [])
        except Exception:
            return None

        if not raw_auctions:
            return MR(item_name=riven_item.name or keyword, payload=None)

        auction_list = []
        for a in raw_auctions:
            if a.get("closed") or not a.get("visible"):
                continue
            owner = a.get("owner", {})
            if owner.get("status") not in ("online", "ingame"):
                continue

            item_data = a.get("item", {})
            attrs = []
            for attr in item_data.get("attributes", []):
                attrs.append(
                    RivenAttribute(
                        value=attr.get("value"),
                        positive=attr.get("positive"),
                        url_name=attr.get("url_name"),
                    )
                )

            auction_list.append(
                RivenAuction(
                    buyout_price=a.get("buyout_price"),
                    starting_price=a.get("starting_price"),
                    top_bid=a.get("top_bid"),
                    visible=a.get("visible"),
                    closed=a.get("closed"),
                    platform=a.get("platform"),
                    id=a.get("id"),
                    item=RivenItem(
                        type=item_data.get("type"),
                        mod_rank=item_data.get("mod_rank"),
                        name=item_data.get("name"),
                        re_rolls=item_data.get("re_rolls"),
                        polarity=item_data.get("polarity"),
                        mastery_level=item_data.get("mastery_level"),
                        attributes=attrs,
                    ),
                    owner=RivenOwner(
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

        return MR(
            item_name=riven_item.name or keyword,
            payload=MarketRivenPayload(auctions=auction_list),
        )

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
        from ..api.api import WF_MARKET_AUCTIONS
        from ..model.market import (
            LichSisterAuction,
            LichSisterItem,
            LichSisterOwner,
            MarketLichSisterPayload,
        )
        from ..model.market import (
            MarketLichSister as MLS,
        )
        from ..util import fetch_json

        # 1. 查找武器
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

        # 2. 构建搜索参数并请求 API
        try:
            resp = await fetch_json(
                WF_MARKET_AUCTIONS,
                params={
                    "type": search_type,
                    "weapon_url_name": slug,
                    "sort_by": "price_asc",
                    "has_ephemera": "false",
                    "element": "any",
                    "damage_min": 25,
                    "damage_max": 60,
                },
                headers={"Content-Type": "application/json", "language": "zh-hans"},
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
    # 缓存（原有，保持不变）
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    def clear_cache(cls) -> None:
        """清除市场数据缓存。"""
        ...  # TODO: 待实现缓存逻辑
