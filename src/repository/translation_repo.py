"""Translation repository / 状态翻译数据访问层"""
from __future__ import annotations

from typing import Optional

from tortoise.exceptions import DoesNotExist

from ..model.state_translation import StateTranslation
from .base import BaseRepository


class StateTranslationRepository(BaseRepository[StateTranslation]):
    """状态翻译数据访问对象。"""

    def __init__(self):
        super().__init__(StateTranslation)

    async def find_by_unique_name(
        self, unique_name: str
    ) -> Optional[StateTranslation]:
        """根据唯一名称查找。"""
        try:
            return await StateTranslation.get(unique_name=unique_name)
        except DoesNotExist:
            return None

    async def search_by_name(
        self, keyword: str, offset: int = 0, limit: int = 100
    ):
        """按名称模糊搜索。"""
        qs = StateTranslation.filter(name__contains=keyword)
        total = await qs.count()
        items = await qs.offset(offset).limit(limit)
        return list(items), total


# 模块级单例
state_translation_repo = StateTranslationRepository()
