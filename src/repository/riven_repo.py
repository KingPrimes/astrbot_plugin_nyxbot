"""Riven repository / 紫卡相关数据访问层"""
from __future__ import annotations

from typing import Optional

from tortoise.exceptions import DoesNotExist
from tortoise.expressions import Q

from ..model.riven_tion import RivenTion
from ..model.riven_tion_alias import RivenTionAlias
from ..model.riven_analyse_trend import RivenAnalyseTrend
from ..model.riven_items import RivenItems
from .base import BaseRepository


class RivenTionRepository(BaseRepository[RivenTion]):
    """紫卡词条参数数据访问对象。"""

    def __init__(self):
        super().__init__(RivenTion)

    async def find_by_effect(self, effect: str) -> Optional[RivenTion]:
        """根据词条效果名称查找。"""
        try:
            return await RivenTion.get(effect=effect)
        except DoesNotExist:
            return None

    async def search_by_keyword(
        self, keyword: str, offset: int = 0, limit: int = 100
    ):
        """模糊搜索词条（名称/URL）。"""
        qs = RivenTion.filter(
            Q(effect__contains=keyword) | Q(url_name__contains=keyword)
        )
        total = await qs.count()
        items = await qs.offset(offset).limit(limit)
        return list(items), total


class RivenTionAliasRepository(BaseRepository[RivenTionAlias]):
    """紫卡词条别名数据访问对象。"""

    def __init__(self):
        super().__init__(RivenTionAlias)

    async def find_by_en(self, en: str) -> Optional[RivenTionAlias]:
        """根据英文查找。"""
        try:
            return await RivenTionAlias.get(en=en)
        except DoesNotExist:
            return None

    async def find_by_cn(self, cn: str) -> Optional[RivenTionAlias]:
        """根据中文查找。"""
        try:
            return await RivenTionAlias.get(cn=cn)
        except DoesNotExist:
            return None


class RivenAnalyseTrendRepository(BaseRepository[RivenAnalyseTrend]):
    """紫卡分析参数数据访问对象。"""

    def __init__(self):
        super().__init__(RivenAnalyseTrend)

    async def find_by_name(self, name: str) -> Optional[RivenAnalyseTrend]:
        """根据效果名称查找。"""
        try:
            return await RivenAnalyseTrend.get(name=name)
        except DoesNotExist:
            return None


class RivenItemsRepository(BaseRepository[RivenItems]):
    """紫卡物品数据访问对象。"""

    def __init__(self):
        super().__init__(RivenItems)

    async def find_by_slug(self, slug: str) -> Optional[RivenItems]:
        """根据 URL slug 查找。"""
        try:
            return await RivenItems.get(slug=slug)
        except DoesNotExist:
            return None

    async def find_by_group(self, group: str) -> list[RivenItems]:
        """根据分组查找。"""
        return await RivenItems.filter(group=group)


# 模块级单例
riven_tion_repo = RivenTionRepository()
riven_tion_alias_repo = RivenTionAliasRepository()
riven_analyse_trend_repo = RivenAnalyseTrendRepository()
riven_items_repo = RivenItemsRepository()
