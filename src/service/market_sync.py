"""Market sync service / 市场数据同步服务

从 Warframe.Market API 拉取数据并同步到本地数据库。

字段映射以 ``src/model/market/entities.py`` 为准（对应官方 data-models 文档），
这里只负责「模型 → 表行」的转换。转换结果**只保留非 None 的键**，配合
``batch_upsert`` 的「缺失字段不更新」语义，避免用 None 覆盖库里已有值。
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable

from astrbot.api import logger

from ..api import MarketClient
from ..model.ephemeras import Ephemeras
from ..model.lich_sister_weapons import LichSisterWeapons
from ..model.market.entities import Ephemera, Item, LichWeapon
from ..model.orders_items import OrdersItems
from ..util.i18n_utils import extract_i18n


def _compact(row: dict) -> dict:
    """丢掉 None 值（id 必须保留）。"""
    return {
        key: value
        for key, value in row.items()
        if value is not None or key == "id"
    }


def _item_row(raw: dict) -> dict:
    """Item 模型 → ordersitems 行。"""
    entity = Item.model_validate(raw)
    row = {
        "id": entity.id,
        "slug": entity.slug,
        "gameRef": entity.game_ref,
        "tags": entity.tags or None,
        "setRoot": entity.set_root,
        "setParts": entity.set_parts or None,
        "quantityInSet": entity.quantity_in_set,
        "rarity": entity.rarity,
        "bulkTradable": entity.bulk_tradable,
        "subtypes": entity.subtypes or None,
        "maxRank": entity.max_rank,
        "maxCharges": entity.max_charges,
        "maxAmberStars": entity.max_amber_stars,
        "maxCyanStars": entity.max_cyan_stars,
        "baseEndo": entity.base_endo,
        "endoMultiplier": entity.endo_multiplier,
        "ducats": entity.ducats,
        "vosfor": entity.vosfor,
        "reqMasteryRank": entity.req_mastery_rank,
        "vaulted": entity.vaulted,
        "tradingTax": entity.trading_tax,
        "tradable": entity.tradable,
    }
    row.update(extract_i18n(raw))
    return _compact(row)


def _lich_weapon_row(raw: dict) -> dict:
    """LichWeapon 模型 → lichsisterweapons 行。"""
    entity = LichWeapon.model_validate(raw)
    row = {
        "id": entity.id,
        "slug": entity.slug,
        "gameRef": entity.game_ref,
        "reqMasteryRank": entity.req_mastery_rank,
    }
    row.update(extract_i18n(raw))
    return _compact(row)


def _ephemera_row(raw: dict) -> dict:
    """Ephemera 模型 → ephemeras 行。"""
    entity = Ephemera.model_validate(raw)
    row = {
        "id": entity.id,
        "slug": entity.slug,
        "gameRef": entity.game_ref,
        "animation": entity.animation,
        "element": entity.element,
    }
    row.update(extract_i18n(raw))
    return _compact(row)


def _update_fields(rows: list[dict]) -> list[str]:
    """本次出现过的所有列（不含主键），交给 batch_upsert 做脏检测。"""
    keys = {key for row in rows for key in row}
    keys.discard("id")
    return sorted(keys)


class MarketSyncService:
    """市场数据同步服务。"""

    @classmethod
    async def sync_orders_items(cls) -> None:
        """同步 OrdersItems（市场订单物品）— 从 ``/v2/items``。"""
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

        rows = [_item_row(item) for item in data]

        total_upserted = await DataSyncService.batch_upsert(
            model_cls=OrdersItems,
            items=rows,
            key_field="id",
            build_instance=lambda row: OrdersItems(**row),
            update_fields=_update_fields(rows),
        )
        total = await OrdersItems.all().count()
        logger.info(f"物品数据初始化完成，共 {total} 条记录（本次处理 {total_upserted} 条）")

    @classmethod
    async def _sync_dual_market_resource(
        cls,
        fetch_lich_fn: Callable,
        fetch_sister_fn: Callable,
        model_cls: type,
        to_row: Callable[[dict], dict],
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
        for resp, label in ((lich_resp, lich_label), (sister_resp, sister_label)):
            if resp:
                chunk = resp.get("data", [])
                all_data.extend(chunk)
                logger.info(f"{label}: {len(chunk)} 条")
            else:
                logger.warning(f"{label}数据为空")

        if not all_data:
            logger.warning(f"无{log_name}数据可插入")
            return

        # 只保留目标表真实存在的列（extract_i18n 会产出 enName 等通用键）
        allowed = set(model_cls._meta.fields_map)
        rows = [
            {k: v for k, v in to_row(item).items() if k in allowed}
            for item in all_data
        ]

        total_upserted = await DataSyncService.batch_upsert(
            model_cls=model_cls,
            items=rows,
            key_field="id",
            build_instance=lambda row: model_cls(**row),
            update_fields=_update_fields(rows),
        )
        total = await model_cls.all().count()
        logger.info(f"{log_name}数据初始化完成，共 {total} 条记录（本次处理 {total_upserted} 条）")

    @classmethod
    async def sync_ephemeras(cls) -> None:
        """同步 Ephemeras（幻纹）— ``/lich/ephemeras`` + ``/sister/ephemeras``。"""
        await cls._sync_dual_market_resource(
            fetch_lich_fn=MarketClient.fetch_lich_ephemeras,
            fetch_sister_fn=MarketClient.fetch_sister_ephemeras,
            model_cls=Ephemeras,
            to_row=_ephemera_row,
            log_name="幻纹",
            lich_label="赤毒幻纹",
            sister_label="信条幻纹",
        )

    @classmethod
    async def sync_lich_sister_weapons(cls) -> None:
        """同步 LichSisterWeapons — ``/lich/weapons`` + ``/sister/weapons``。"""
        await cls._sync_dual_market_resource(
            fetch_lich_fn=MarketClient.fetch_lich_weapons,
            fetch_sister_fn=MarketClient.fetch_sister_weapons,
            model_cls=LichSisterWeapons,
            to_row=_lich_weapon_row,
            log_name="信条/赤毒武器",
            lich_label="赤毒武器",
            sister_label="信条武器",
        )
