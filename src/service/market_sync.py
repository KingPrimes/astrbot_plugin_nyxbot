"""Market sync service / 市场数据同步服务

从 Warframe.Market API 拉取数据并同步到本地数据库。
"""
from __future__ import annotations

import asyncio

from astrbot.api import logger

from ..api import MarketClient
from ..model.ephemeras import Ephemeras
from ..model.lich_sister_weapons import LichSisterWeapons
from ..model.orders_items import OrdersItems


class MarketSyncService:
    """市场数据同步服务。"""

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

        items: list[dict] = [{**item, **cls._extract_i18n(item)} for item in data]

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

        lich_resp, sister_resp = await asyncio.gather(
            MarketClient.fetch_lich_ephemeras(),
            MarketClient.fetch_sister_ephemeras(),
        )

        all_data: list[dict] = []

        if lich_resp:
            lich_data = lich_resp.get("data", [])
            all_data.extend({**item, **cls._extract_i18n(item)} for item in lich_data)
            logger.info(f"赤毒幻纹: {len(lich_data)} 条")
        else:
            logger.warning("赤毒幻纹数据为空")

        if sister_resp:
            sister_data = sister_resp.get("data", [])
            all_data.extend({**item, **cls._extract_i18n(item)} for item in sister_data)
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

        lich_resp, sister_resp = await asyncio.gather(
            MarketClient.fetch_lich_weapons(),
            MarketClient.fetch_sister_weapons(),
        )

        all_data: list[dict] = []

        if lich_resp:
            lich_data = lich_resp.get("data", [])
            all_data.extend({**item, **cls._extract_i18n(item)} for item in lich_data)
            logger.info(f"赤毒武器: {len(lich_data)} 条")
        else:
            logger.warning("赤毒武器数据为空")

        if sister_resp:
            sister_data = sister_resp.get("data", [])
            all_data.extend({**item, **cls._extract_i18n(item)} for item in sister_data)
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
