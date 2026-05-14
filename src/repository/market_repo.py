"""Market repository / 市场相关数据访问层"""
from __future__ import annotations

from typing import Optional

from tortoise.exceptions import DoesNotExist

from ..model.orders_items import OrdersItems
from ..model.ephemeras import Ephemeras
from ..model.lich_sister_weapons import LichSisterWeapons
from .base import BaseRepository


class OrdersItemsRepository(BaseRepository[OrdersItems]):
    """市场订单物品数据访问对象。"""

    def __init__(self):
        super().__init__(OrdersItems)

    async def find_by_slug(self, slug: str) -> Optional[OrdersItems]:
        """根据 URL slug 查找。"""
        try:
            return await OrdersItems.get(slug=slug)
        except DoesNotExist:
            return None

    async def search_by_name(
        self, keyword: str, offset: int = 0, limit: int = 100
    ):
        """按名称模糊搜索。"""
        qs = OrdersItems.filter(name__contains=keyword)
        total = await qs.count()
        items = await qs.offset(offset).limit(limit)
        return list(items), total


class EphemerasRepository(BaseRepository[Ephemeras]):
    """幻纹数据访问对象。"""

    def __init__(self):
        super().__init__(Ephemeras)

    async def find_by_name(self, name: str) -> Optional[Ephemeras]:
        """根据名称查找。"""
        try:
            return await Ephemeras.get(name=name)
        except DoesNotExist:
            return None


class LichSisterWeaponsRepository(BaseRepository[LichSisterWeapons]):
    """信条/赤毒武器数据访问对象。"""

    def __init__(self):
        super().__init__(LichSisterWeapons)

    async def find_by_name(self, name: str) -> Optional[LichSisterWeapons]:
        """根据名称查找。"""
        try:
            return await LichSisterWeapons.get(name=name)
        except DoesNotExist:
            return None


# 模块级单例
orders_items_repo = OrdersItemsRepository()
ephemeras_repo = EphemerasRepository()
lich_sister_weapons_repo = LichSisterWeaponsRepository()
