"""Market ducats service / 杜卡币服务

镜像 Java: MarketDucatsUtils
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from tortoise.exceptions import DoesNotExist

from astrbot.api import logger

from ..model.orders_items import OrdersItems

if TYPE_CHECKING:
    from ..model.market import DucatItem, Ducats


class MarketDucatsService:
    """杜卡币查询服务。"""

    @classmethod
    async def get_ducats_data(cls) -> Ducats | None:
        """获取杜卡币原始数据 — 镜像 Java getDucats()。

        Returns:
            Ducats 模型实例，失败时返回 None。
        """
        from ..api.api import WF_MARKET_DUCATS
        from ..model.market import Ducats
        from ..util import async_cached, fetch_json, market_cache

        try:
            resp = await async_cached(
                "ducats",
                lambda: fetch_json(WF_MARKET_DUCATS),
                market_cache,
            )
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
    async def _resolve_ducat_item_names(cls, items: list[DucatItem]) -> None:
        """从本地 OrdersItems 表解析物品名称 — 镜像 Java peek(d -> d.setItem(...))"""
        for d in items:
            if not d.item:
                continue
            try:
                order_item = await OrdersItems.get(id=d.item)
                d.item_name = order_item.name or d.item
            except DoesNotExist:
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
        await cls._resolve_ducat_item_names(day_items)
        await cls._resolve_ducat_item_names(hour_items)
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
        await cls._resolve_ducat_item_names(day_items)
        await cls._resolve_ducat_item_names(hour_items)
        return day_items, hour_items
