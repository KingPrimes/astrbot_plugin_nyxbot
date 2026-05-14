"""Alias repository / 别名数据访问层"""
from __future__ import annotations

from typing import Optional

from tortoise.exceptions import DoesNotExist

from ..model.alias import Alias
from .base import BaseRepository


class AliasRepository(BaseRepository[Alias]):
    """别名表数据访问对象。"""

    def __init__(self):
        super().__init__(Alias)

    async def find_by_cn(self, cn: str) -> Optional[Alias]:
        """根据中文名称查找。"""
        try:
            return await Alias.get(cn=cn)
        except DoesNotExist:
            return None

    async def find_by_en(self, en: str) -> Optional[Alias]:
        """根据英文名称查找。"""
        try:
            return await Alias.get(en=en)
        except DoesNotExist:
            return None

    async def search_by_keyword(
        self, keyword: str, offset: int = 0, limit: int = 100
    ):
        """模糊搜索别名（同时搜索中文和英文）。"""
        from tortoise.expressions import Q
        qs = Alias.filter(
            Q(cn__contains=keyword) | Q(en__contains=keyword)
        )
        total = await qs.count()
        items = await qs.offset(offset).limit(limit)
        return list(items), total


# 模块级单例
alias_repo = AliasRepository()
