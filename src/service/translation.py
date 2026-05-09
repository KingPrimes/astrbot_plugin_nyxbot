"""Translation service / 翻译服务

提供 Warframe 物品名称的中英文翻译查询。
"""
from __future__ import annotations

from typing import Optional

from ..init import get_session
from ..repository.alias_repo import alias_repo


class TranslationService:
    """翻译服务：中英文名称互查。"""

    @classmethod
    async def cn_to_en(cls, cn_name: str) -> Optional[str]:
        """中文名 → 英文名。

        Args:
            cn_name: 中文名称。

        Returns:
            英文名称，未找到返回 None。
        """
        async with get_session() as session:
            alias = await alias_repo.find_by_cn(session, cn_name)
            return alias.en if alias else None

    @classmethod
    async def en_to_cn(cls, en_name: str) -> Optional[str]:
        """英文名 → 中文名。

        Args:
            en_name: 英文名称。

        Returns:
            中文名称，未找到返回 None。
        """
        async with get_session() as session:
            alias = await alias_repo.find_by_en(session, en_name)
            return alias.cn if alias else None

    @classmethod
    async def search(cls, keyword: str, page: int = 1, page_size: int = 20):
        """模糊搜索。

        Args:
            keyword: 搜索关键词。
            page: 页码。
            page_size: 每页大小。

        Returns:
            (结果列表, 总数) 的元组。
        """
        async with get_session() as session:
            return await alias_repo.search_by_keyword(
                session, keyword, (page - 1) * page_size, page_size
            )
