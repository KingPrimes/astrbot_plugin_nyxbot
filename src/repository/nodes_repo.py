"""Nodes repository / 星图节点数据访问层"""
from __future__ import annotations

from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..model.nodes import Nodes
from .base import BaseRepository


class NodesRepository(BaseRepository[Nodes]):
    """星图节点数据访问对象。"""

    def __init__(self):
        super().__init__(Nodes)

    async def find_by_name(self, session: AsyncSession, name: str) -> Optional[Nodes]:
        """根据节点名称查找。"""
        stmt = select(Nodes).where(Nodes.name == name)
        result = await session.exec(stmt)
        return result.first()

    async def find_by_unique_name(self, session: AsyncSession, unique_name: str) -> Optional[Nodes]:
        """根据唯一标识查找。"""
        return await self.get_by_id(session, unique_name)


# 模块级单例
nodes_repo = NodesRepository()
