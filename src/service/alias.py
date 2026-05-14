"""Alias service / 别名服务层"""
from __future__ import annotations

from typing import Optional

from ..model.alias import Alias


class AliasService:
    """别名查询/管理服务。"""

    @classmethod
    async def find_by_cn(cls, cn: str) -> Optional[Alias]:
        """根据中文名称查找别名。"""
        ...

    @classmethod
    async def find_by_en(cls, en: str) -> Optional[Alias]:
        """根据英文名称查找别名。"""
        ...

    @classmethod
    async def search(cls, keyword: str, page: int = 1, page_size: int = 20):
        """模糊搜索别名。

        Returns:
            (记录列表, 总记录数) 的元组。
        """
        ...

    @classmethod
    async def list_all(cls, page: int = 1, page_size: int = 20):
        """分页查询所有别名。

        Returns:
            (记录列表, 总记录数) 的元组。
        """
        ...

    @classmethod
    async def add(cls, cn: str, en: str) -> Alias:
        """添加别名。"""
        ...

    @classmethod
    async def update(cls, alias_id: int, cn: str, en: str) -> Optional[Alias]:
        """更新别名。"""
        ...

    @classmethod
    async def delete(cls, alias_id: int) -> bool:
        """删除别名。"""
        ...

    @classmethod
    async def sync_from_cdn(cls) -> int:
        """从 CDN 重新同步别名数据。

        Returns:
            同步后的记录总数。
        """
        ...
