"""Base repository / 仓库基类

提供通用的 TortoiseORM CRUD 操作。
"""
from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

from tortoise.exceptions import DoesNotExist
from tortoise.models import Model

T = TypeVar("T", bound=Model)


class BaseRepository(Generic[T]):
    """仓库基类，封装通用 CRUD 操作。"""

    def __init__(self, model_cls: type[T]) -> None:
        self._model_cls = model_cls

    async def get_by_id(self, id_val: Any) -> Optional[T]:
        """根据主键获取记录。"""
        try:
            return await self._model_cls.get(id=id_val)
        except DoesNotExist:
            return None

    async def list_all(
        self,
        offset: int = 0,
        limit: int = 100,
        order_field: Optional[str] = None,
    ) -> tuple[list[T], int]:
        """分页查询所有记录。

        Returns:
            (记录列表, 总记录数) 的元组。
        """
        qs = self._model_cls.all()
        total = await qs.count()
        if order_field:
            qs = qs.order_by(order_field)
        items = await qs.offset(offset).limit(limit)
        return list(items), total

    async def add(self, instance: T) -> T:
        """添加新记录。"""
        await instance.save()
        return instance

    async def update(self, instance: T) -> T:
        """更新已有记录。"""
        await instance.save()
        return instance

    async def delete(self, id_val: Any) -> bool:
        """根据主键删除记录。"""
        deleted = await self._model_cls.filter(id=id_val).delete()
        return deleted > 0

    async def delete_all(self) -> int:
        """清空表数据。

        Returns:
            删除的记录数。
        """
        return await self._model_cls.all().delete()

    async def search(
        self,
        conditions: dict[str, Any] | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[T], int]:
        """带条件的分页查询。

        Args:
            conditions: TortoiseORM filter kwargs（如 {"cn__contains": "xxx"}）。
            offset: 偏移量。
            limit: 每页大小。

        Returns:
            (记录列表, 总记录数) 的元组。
        """
        qs = self._model_cls.all()
        if conditions:
            qs = qs.filter(**conditions)
        total = await qs.count()
        items = await qs.offset(offset).limit(limit)
        return list(items), total
