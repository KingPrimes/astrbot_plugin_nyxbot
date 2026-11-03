"""DataSync service / 数据同步服务

提供批量 upsert 操作，供 init 层调用。
"""
from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from tortoise.models import Model as TortoiseModel

from astrbot.api import logger

from ..init.engine import get_engine

_T = TypeVar("_T", bound=TortoiseModel)

_BATCH_SIZE = 1000
# SQLite 参数上限 999，__in 查询分片大小需小于此值
_IN_QUERY_CHUNK_SIZE = 500

_SQLITE_MAX_VARIABLES = 999


def _safe_update_batch_size(num_fields: int) -> int:
    """计算 bulk_update 的安全批次大小。

    TortoiseORM 的 bulk_update 使用 CASE WHEN 语法，
    每条记录产生 (1 + num_fields) 个 SQL 参数：
    1 个 PK 匹配 + N 个字段 THEN 值。
    """
    return _SQLITE_MAX_VARIABLES // (1 + num_fields)


async def _fetch_existing_chunked(
    model_cls: type[TortoiseModel],
    key_field: str,
    keys: list,
) -> dict:
    """分批 __in 查询，避免超过 SQLite 参数上限 (999)。"""
    result: dict = {}
    for i in range(0, len(keys), _IN_QUERY_CHUNK_SIZE):
        chunk = keys[i : i + _IN_QUERY_CHUNK_SIZE]
        async for obj in model_cls.filter(**{f"{key_field}__in": chunk}):
            result[getattr(obj, key_field)] = obj
    return result


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
        prune: bool = False,
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
            prune: 是否删除本次数据里不存在的旧行。适用于「整份快照」型数据源
                   （如 alias/nodes），增量导入时被上游删掉的条目不会自动消失。
                   为安全起见，本次数据为空时不做删除。

        Returns:
            (new_count, updated_count) — 本次新增数量和更新数量。
        """
        from tortoise.transactions import in_transaction

        async def _do_upsert() -> tuple[int, int]:
            await get_engine()

            # 查询已存在的 key 集合（分片避免 SQLite 参数上限）
            keys = [item[key_field] for item in data if item.get(key_field)]
            existing_map: dict[str, _T] = (
                await _fetch_existing_chunked(model_cls, key_field, keys)
            )

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
            # bulk_update 使用 CASE WHEN 语法，需分批避免 SQLite 参数上限
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
                    changed = False
                    for field in update_fields:
                        new_val = item.get(field)
                        if getattr(obj, field) != new_val:
                            setattr(obj, field, new_val)
                            changed = True
                    if changed:
                        to_update.append(obj)
                if to_update:
                    update_chunk = _safe_update_batch_size(len(update_fields))
                    for i in range(0, len(to_update), update_chunk):
                        chunk = to_update[i : i + update_chunk]
                        await model_cls.bulk_update(chunk, fields=update_fields)
                    updated_count = len(to_update)

            # Prune: 删除本次快照里已不存在的旧行（仅整份快照型数据源）
            # 注意不能拿 existing_map 做差集——它只包含本次 keys 命中的行
            if prune and keys:
                db_keys = set(
                    await model_cls.all().values_list(key_field, flat=True)
                )
                stale = db_keys - set(keys)
                if stale:
                    stale_list = list(stale)
                    for i in range(0, len(stale_list), _BATCH_SIZE):
                        chunk = stale_list[i : i + _BATCH_SIZE]
                        await model_cls.filter(**{f"{key_field}__in": chunk}).delete()
                    logger.info(f"{model_cls.__name__} 清理 {len(stale_list)} 条已消失的记录")

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
            # --- 先查询已存在的 keys（分片避免 SQLite 参数上限）---
            keys = [item[key_field] for item in items]
            existing_map = await _fetch_existing_chunked(
                model_cls, key_field, keys
            )

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
            # bulk_update 使用 CASE WHEN 语法，每条记录产生 (1+N_fields) 个 SQL 参数
            up_batch = min(batch_size, _safe_update_batch_size(len(update_fields)))
            to_update: list[_T] = []
            for item in items:
                obj = existing_map.get(item[key_field])
                if obj is not None:
                    changed = False
                    for field in update_fields:
                        new_val = item.get(field)
                        if getattr(obj, field) != new_val:
                            setattr(obj, field, new_val)
                            changed = True
                    if changed:
                        to_update.append(obj)
                        if len(to_update) >= up_batch:
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
