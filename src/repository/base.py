"""Base repository / 仓库基类

提供通用的 SQLModel CRUD 操作封装。
"""
from __future__ import annotations

from typing import Any, Generic, Optional, Sequence, TypeVar

from sqlmodel import SQLModel, select, func, delete as sql_delete
from sqlmodel.ext.asyncio.session import AsyncSession

from ..init import get_session

T = TypeVar("T", bound=SQLModel)


class BaseRepository(Generic[T]):
    """仓库基类，封装通用 CRUD 操作。"""

    def __init__(self, model_cls: type[T]) -> None:
        self._model_cls = model_cls

    async def get_by_id(self, session: AsyncSession, id_val: Any) -> Optional[T]:
        """根据主键获取记录。"""
        return await session.get(self._model_cls, id_val)

    async def list_all(
        self,
        session: AsyncSession,
        offset: int = 0,
        limit: int = 100,
        order_field: Optional[str] = None,
    ) -> tuple[list[T], int]:
        """分页查询所有记录。

        Returns:
            (记录列表, 总记录数) 的元组。
        """
        # 查询总数
        count_stmt = select(func.count()).select_from(self._model_cls)
        total = (await session.exec(count_stmt)).one()

        # 分页查询
        stmt = select(self._model_cls).offset(offset).limit(limit)
        if order_field:
            stmt = stmt.order_by(order_field)
        results = await session.exec(stmt)
        return list(results.all()), total

    async def add(self, session: AsyncSession, instance: T) -> T:
        """添加新记录。"""
        session.add(instance)
        await session.commit()
        await session.refresh(instance)
        return instance

    async def update(self, session: AsyncSession, instance: T) -> T:
        """更新已有记录。"""
        session.add(instance)
        await session.commit()
        await session.refresh(instance)
        return instance

    async def delete(self, session: AsyncSession, id_val: Any) -> bool:
        """根据主键删除记录。"""
        instance = await self.get_by_id(session, id_val)
        if instance is None:
            return False
        await session.delete(instance)
        await session.commit()
        return True

    async def delete_all(self, session: AsyncSession) -> int:
        """清空表数据。

        Returns:
            删除的记录数。
        """
        result = await session.exec(sql_delete(self._model_cls))
        await session.commit()
        return result.rowcount

    async def search(
        self,
        session: AsyncSession,
        conditions: list,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[T], int]:
        """带条件的分页查询。

        Args:
            session: 数据库会话。
            conditions: SQLModel 条件列表（如 [Alias.cn == "xxx"]）。
            offset: 偏移量。
            limit: 每页大小。

        Returns:
            (记录列表, 总记录数) 的元组。
        """
        # 总数
        count_stmt = select(func.count()).select_from(self._model_cls).where(*conditions)
        total = (await session.exec(count_stmt)).one()

        # 查询
        stmt = select(self._model_cls).where(*conditions).offset(offset).limit(limit)
        results = await session.exec(stmt)
        return list(results.all()), total
