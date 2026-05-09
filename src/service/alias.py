"""Alias service / 别名服务层"""
from __future__ import annotations

from typing import Optional

from ..init import get_session
from ..repository import alias_repo
from ..model.alias import Alias


class AliasService:
    """别名查询/管理服务。"""

    @classmethod
    async def find_by_cn(cls, cn: str) -> Optional[Alias]:
        """根据中文名称查找别名。"""
        async with get_session() as session:
            return await alias_repo.find_by_cn(session, cn)

    @classmethod
    async def find_by_en(cls, en: str) -> Optional[Alias]:
        """根据英文名称查找别名。"""
        async with get_session() as session:
            return await alias_repo.find_by_en(session, en)

    @classmethod
    async def search(cls, keyword: str, page: int = 1, page_size: int = 20):
        """模糊搜索别名。"""
        offset = (page - 1) * page_size
        async with get_session() as session:
            items, total = await alias_repo.search_by_keyword(
                session, keyword, offset, page_size
            )
            return items, total

    @classmethod
    async def list_all(cls, page: int = 1, page_size: int = 20):
        """分页查询所有别名。"""
        offset = (page - 1) * page_size
        async with get_session() as session:
            items, total = await alias_repo.list_all(session, offset, page_size)
            return items, total

    @classmethod
    async def add(cls, cn: str, en: str) -> Alias:
        """添加别名。"""
        alias = Alias(cn=cn, en=en)
        async with get_session() as session:
            return await alias_repo.add(session, alias)

    @classmethod
    async def update(cls, alias_id: int, cn: str, en: str) -> Optional[Alias]:
        """更新别名。"""
        async with get_session() as session:
            existing = await alias_repo.get_by_id(session, alias_id)
            if not existing:
                return None
            existing.cn = cn
            existing.en = en
            return await alias_repo.update(session, existing)

    @classmethod
    async def delete(cls, alias_id: int) -> bool:
        """删除别名。"""
        async with get_session() as session:
            return await alias_repo.delete(session, alias_id)

    @classmethod
    async def sync_from_cdn(cls) -> int:
        """从 CDN 重新同步别名数据。

        Returns:
            同步的记录数。
        """
        from ..init import init_alias_data
        await init_alias_data()
        # 同步后查询总数
        async with get_session() as session:
            _, total = await alias_repo.list_all(session, 0, 1)
            return total
