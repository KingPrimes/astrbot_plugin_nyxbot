"""Nodes repository / 星图节点数据访问层"""
from __future__ import annotations

from typing import Optional

from tortoise.exceptions import DoesNotExist

from ..model.export.nodes import ExprotNodes as Nodes
from .base import BaseRepository


class NodesRepository(BaseRepository[Nodes]):
    """星图节点数据访问对象。"""

    def __init__(self):
        super().__init__(Nodes)

    async def find_by_name(self, name: str) -> Optional[Nodes]:
        """根据节点名称查找。"""
        try:
            return await Nodes.get(name=name)
        except DoesNotExist:
            return None

    async def find_by_unique_name(
        self, uniqueName: str
    ) -> Optional[Nodes]:
        """根据唯一标识查找。"""
        try:
            return await Nodes.get(uniqueName=uniqueName)
        except DoesNotExist:
            return None


# 模块级单例
nodes_repo = NodesRepository()
