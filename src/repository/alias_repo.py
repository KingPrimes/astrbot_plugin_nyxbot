"""Alias repository / 别名数据访问层"""
from __future__ import annotations

from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..model.alias import Alias
from .base import BaseRepository


class AliasRepository(BaseRepository[Alias]):
    """别名表数据访问对象。"""

    def __init__(self):
        super().__init__(Alias)

    async def find_by_cn(self, session: AsyncSession, cn: str) -> Optional[Alias]:
        """根据中文名称查找。"""
        stmt = select(Alias).where(Alias.cn == cn)
        result = await session.exec(stmt)
        return result.first()

    async def find_by_en(self, session: AsyncSession, en: str) -> Optional[Alias]:
        """根据英文名称查找。"""
        stmt = select(Alias).where(Alias.en == en)
        result = await session.exec(stmt)
        return result.first()

    async def search_by_keyword(
        self, session: AsyncSession, keyword: str, offset: int = 0, limit: int = 100
    ):
        """模糊搜索别名（同时搜索中文和英文）。"""
        from sqlmodel import or_
        pattern = f"%{keyword}%"
        conditions = [or_(Alias.cn.like(pattern), Alias.en.like(pattern))]
        return await self.search(session, conditions, offset, limit)


# 模块级单例
alias_repo = AliasRepository()
