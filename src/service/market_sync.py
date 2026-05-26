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
from ..util.i18n_utils import extract_i18n


class MarketSyncService:
    """市场数据同步服务。"""

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

        items: list[dict] = [{**item, **extract_i18n(item)} for item in data]

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
    async def _sync_dual_market_resource(
        cls,
        fetch_lich_fn,
        fetch_sister_fn,
        model_cls,
        build_instance,
        update_fields: list[str],
        log_name: str,
        lich_label: str,
        sister_label: str,
    ) -> None:
        """通用双端（赤毒+信条）Market 资源同步骨架。"""
        from ..init.engine import get_engine
        from .data_sync import DataSyncService

        logger.info(f"从 Market API 加载{log_name}数据...")
        await get_engine()

        lich_resp, sister_resp = await asyncio.gather(
            fetch_lich_fn(), fetch_sister_fn(),
        )

        all_data: list[dict] = []

        if lich_resp:
            lich_data = lich_resp.get("data", [])
            all_data.extend({**item, **extract_i18n(item)} for item in lich_data)
            logger.info(f"{lich_label}: {len(lich_data)} 条")
        else:
            logger.warning(f"{lich_label}数据为空")

        if sister_resp:
            sister_data = sister_resp.get("data", [])
            all_data.extend({**item, **extract_i18n(item)} for item in sister_data)
            logger.info(f"{sister_label}: {len(sister_data)} 条")
        else:
            logger.warning(f"{sister_label}数据为空")

        if not all_data:
            logger.warning(f"无{log_name}数据可插入")
            return

        total_upserted = await DataSyncService.batch_upsert(
            model_cls=model_cls,
            items=all_data,
            key_field="id",
            build_instance=build_instance,
            update_fields=update_fields,
        )
        total = await model_cls.all().count()
        logger.info(f"{log_name}数据初始化完成，共 {total} 条记录（本次处理 {total_upserted} 条）")

    @classmethod
    async def sync_ephemeras(cls) -> None:
        """初始化 Ephemeras（幻纹）表数据 — 从 Market API。

        从 /lich/ephemeras 和 /sister/ephemeras 两个端点并发获取数据，
        合并后统一 batch_upsert。
        """
        await cls._sync_dual_market_resource(
            fetch_lich_fn=MarketClient.fetch_lich_ephemeras,
            fetch_sister_fn=MarketClient.fetch_sister_ephemeras,
            model_cls=Ephemeras,
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
            log_name="幻纹",
            lich_label="赤毒幻纹",
            sister_label="信条幻纹",
        )

    @classmethod
    async def sync_lich_sister_weapons(cls) -> None:
        """初始化 LichSisterWeapons（信条/赤毒武器）表数据 — 从 Market API。

        从 /lich/weapons 和 /sister/weapons 两个端点并发获取数据，
        合并后统一 batch_upsert。
        """
        await cls._sync_dual_market_resource(
            fetch_lich_fn=MarketClient.fetch_lich_weapons,
            fetch_sister_fn=MarketClient.fetch_sister_weapons,
            model_cls=LichSisterWeapons,
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
            log_name="信条/赤毒武器",
            lich_label="赤毒武器",
            sister_label="信条武器",
        )
