"""DataAdmin service / 通用数据管理服务

提供跨模型的 CRUD 操作，供 web_api 调用。
"""
from __future__ import annotations

from typing import Any

from tortoise.expressions import Q
from tortoise.models import Model

from ..init.engine import get_engine


class DataAdminService:
    """通用数据管理服务 — 提供跨模型的 CRUD 操作。"""

    @staticmethod
    async def query(
        model_cls: type[Model],
        search_fields: list[str],
        page: int = 1,
        size: int = 20,
        q: str = "",
    ) -> tuple[list[Model], int]:
        """分页查询（支持多字段模糊搜索）。

        Args:
            model_cls: TortoiseORM 模型类。
            search_fields: 可搜索的字段名列表。
            page: 页码（1-based）。
            size: 每页大小。
            q: 搜索关键词（空字符串表示不搜索）。

        Returns:
            (记录列表, 总记录数) 的元组。
        """
        await get_engine()

        offset = (page - 1) * size

        qs = model_cls.all()
        if q and search_fields:
            field_conditions = []
            for field_name in search_fields:
                field_conditions.append(Q(**{f"{field_name}__contains": q}))
            if field_conditions:
                q_or = field_conditions[0]
                for fc in field_conditions[1:]:
                    q_or |= fc
                qs = qs.filter(q_or)

        total = await qs.count()
        items = await qs.offset(offset).limit(size)
        return list(items), total

    @staticmethod
    async def create(model_cls: type[Model], data: dict[str, Any]) -> Model:
        """创建记录。

        Args:
            model_cls: TortoiseORM 模型类。
            data: 字段-值映射。

        Returns:
            创建的模型实例。
        """
        await get_engine()
        instance = model_cls(**data)
        await instance.save()
        return instance

    @staticmethod
    async def update(
        model_cls: type[Model],
        record_id: Any,
        data: dict[str, Any],
    ) -> Model:
        """更新记录（部分字段）。

        Args:
            model_cls: TortoiseORM 模型类。
            record_id: 主键值。
            data: 要更新的字段-值映射。

        Returns:
            更新后的模型实例。

        Raises:
            ValueError: 记录不存在时抛出。
        """
        await get_engine()

        instance = await model_cls.get(id=record_id)
        if not instance:
            raise ValueError(f"Record {record_id} not found in {model_cls.__name__}")

        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        await instance.save()
        return instance

    @staticmethod
    async def delete(model_cls: type[Model], record_id: Any) -> bool:
        """删除记录。

        Args:
            model_cls: TortoiseORM 模型类。
            record_id: 主键值。

        Returns:
            True 表示成功删除，False 表示记录不存在。
        """
        await get_engine()
        deleted = await model_cls.filter(id=record_id).delete()
        return deleted > 0
