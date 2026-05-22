"""DataSync service / 数据同步服务

提供批量 upsert 操作，供 init 层调用。
"""
from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from tortoise.models import Model as TortoiseModel

from ..init.engine import get_engine

_T = TypeVar("_T", bound=TortoiseModel)

_BATCH_SIZE = 1000


class DataSyncService:
    """数据同步服务 — 批量 upsert 操作。"""

    @staticmethod
    async def simple_upsert(
        model_cls: type[_T],
        data: list[dict],
        key_field: str,
        build_instance: Callable[[dict], _T],
        *,
        update_fields: list[str] | None = None,
        use_transaction: bool = True,
    ) -> tuple[int, int]:
        """简单去重 upsert（单 key 去重 + 可选脏检测更新）。

        Args:
            model_cls: TortoiseORM 模型类。
            data: 待插入的数据列表（dict 列表）。
            key_field: 去重字段（如 "cn"、"url_name"、"name"）。
            build_instance: 从 dict 构建模型实例的工厂函数。
            update_fields: 如果提供，对已有记录做脏检测+更新；
                           如果为 None，仅插入不更新（保持原有行为）。
            use_transaction: 是否用显式事务包裹。默认 True。

        Returns:
            (new_count, updated_count) — 本次新增数量和更新数量。
        """
        from tortoise.transactions import in_transaction

        async def _do_upsert() -> tuple[int, int]:
            await get_engine()

            # 查询已存在的 key 集合
            keys = [item[key_field] for item in data if item.get(key_field)]
            existing_map: dict[str, _T] = {
                getattr(row, key_field): row
                async for row in model_cls.filter(**{f"{key_field}__in": keys})
            }

            # Insert: 构建新实例并批量插入
            new_instances = [
                build_instance(item)
                for item in data
                if item.get(key_field) and item[key_field] not in existing_map
            ]
            new_count = 0
            if new_instances:
                created = await model_cls.bulk_create(new_instances)
                new_count = len(created) if created else 0

            # Update: 脏检测（仅当提供 update_fields 时）
            updated_count = 0
            if update_fields:
                to_update: list[_T] = []
                for item in data:
                    key = item.get(key_field)
                    if not key:
                        continue
                    obj = existing_map.get(key)
                    if obj is None:
                        continue
                    new_inst = build_instance(item)
                    changed = False
                    for field in update_fields:
                        if getattr(obj, field) != getattr(new_inst, field):
                            setattr(obj, field, getattr(new_inst, field))
                            changed = True
                    if changed:
                        to_update.append(obj)
                if to_update:
                    await model_cls.bulk_update(to_update, fields=update_fields)
                    updated_count = len(to_update)

            return new_count, updated_count

        if use_transaction:
            async with in_transaction():
                return await _do_upsert()
        else:
            return await _do_upsert()

    @staticmethod
    async def batch_upsert(
        model_cls: type[_T],
        items: list[dict],
        key_field: str,
        build_instance: Callable[[dict], _T],
        update_fields: list[str],
        batch_size: int = _BATCH_SIZE,
        *,
        use_transaction: bool = True,
    ) -> int:
        """分批 Upsert（Phase A bulk_create + Phase B 脏检测 bulk_update）。

        Args:
            model_cls: TortoiseORM 模型类。
            items: 待 upsert 的数据字典列表。
            key_field: 唯一键字段名（如 "uniqueName" 或 "id"）。
            build_instance: 从 dict 构建模型实例的工厂函数。
            update_fields: Phase B 需要比较并更新的字段列表。
            batch_size: 批处理大小，默认 _BATCH_SIZE。
            use_transaction: 是否用显式事务包裹整个 upsert。默认 True
                             以保证原子性；如果外部已有事务可设为 False。

        Returns:
            本次处理的记录总数（Phase A 新增 + Phase B 实际变更数）。
        """
        from tortoise.transactions import in_transaction

        async def _do_upsert() -> int:
            # --- 先查询已存在的 keys（用于可靠计数 + Phase B 脏检测）---
            keys = [item[key_field] for item in items]
            existing_map = {
                getattr(obj, key_field): obj
                async for obj in model_cls.filter(**{f"{key_field}__in": keys})
            }

            # Phase A 前的新增数 = 不在 existing_map 中的 key 数
            total_new = sum(
                1 for item in items if item[key_field] not in existing_map
            )

            # --- Phase A: bulk_create(ignore_conflicts=True) 批量插入新记录 ---
            batch: list[_T] = []
            for item in items:
                if item[key_field] not in existing_map:
                    batch.append(build_instance(item))
                    if len(batch) >= batch_size:
                        await model_cls.bulk_create(batch, ignore_conflicts=True)
                        batch.clear()
            if batch:
                await model_cls.bulk_create(batch, ignore_conflicts=True)

            # --- Phase B: 脏检测 + 分批 bulk_update ---
            to_update: list[_T] = []
            for item in items:
                obj = existing_map.get(item[key_field])
                if obj is not None:
                    # 构建新实例用于值比较
                    new_instance = build_instance(item)
                    changed = False
                    for field in update_fields:
                        old_val = getattr(obj, field)
                        new_val = getattr(new_instance, field)
                        if old_val != new_val:
                            setattr(obj, field, new_val)
                            changed = True
                    if changed:
                        to_update.append(obj)
                        if len(to_update) >= batch_size:
                            await model_cls.bulk_update(to_update, fields=update_fields)
                            total_new += len(to_update)
                            to_update.clear()
            if to_update:
                await model_cls.bulk_update(to_update, fields=update_fields)
                total_new += len(to_update)

            return total_new

        if use_transaction:
            async with in_transaction():
                return await _do_upsert()
        else:
            return await _do_upsert()
