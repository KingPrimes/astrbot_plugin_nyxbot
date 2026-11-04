"""
Tortoise ORM Engine Lifecycle / Tortoise ORM 引擎生命周期

提供数据库引擎的单例初始化、关闭，以及初始化完成信号量。
从 data_sources_init.py 中抽离，消除 service 层对 init 层的循环依赖。
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from tortoise import Tortoise, connections
from tortoise.context import get_current_context, set_global_context
from tortoise.exceptions import ConfigurationError

from astrbot.api import logger

from ..config import get_db_debug
from ..util import get_public_data_path

# ============================================================
# 初始化完成信号量（供命令/API 等待初始化完成）
# ============================================================
_init_complete: asyncio.Event | None = None


def _get_init_event() -> asyncio.Event:
    """惰性获取 Event，避免模块导入时绑定事件循环。"""
    global _init_complete
    if _init_complete is None:
        _init_complete = asyncio.Event()
    return _init_complete


def set_init_complete() -> None:
    """标记初始化完成，唤醒所有等待者。"""
    _get_init_event().set()


async def init_ready() -> None:
    """阻塞等待直到数据初始化完成。命令执行前可调用此函数确保数据就绪。"""
    await _get_init_event().wait()


# 需要补列的升级项：(表名, 列名, 建列语句片段)
_SCHEMA_UPGRADES: tuple[tuple[str, str, str], ...] = (
    ("alias", "is_custom", "INTEGER NOT NULL DEFAULT 0"),
    # ── ordersitems：对齐 API 的 Item 模型 ──
    ("ordersitems", "enName", "VARCHAR(255)"),
    ("ordersitems", "tags", "TEXT"),
    ("ordersitems", "setRoot", "INTEGER"),
    ("ordersitems", "setParts", "TEXT"),
    ("ordersitems", "quantityInSet", "INTEGER"),
    ("ordersitems", "rarity", "VARCHAR(50)"),
    ("ordersitems", "subtypes", "TEXT"),
    ("ordersitems", "maxCharges", "INTEGER"),
    ("ordersitems", "endoMultiplier", "REAL"),
    ("ordersitems", "vosfor", "INTEGER"),
    ("ordersitems", "tradable", "INTEGER"),
    ("ordersitems", "subIcon", "VARCHAR(500)"),
    ("ordersitems", "description", "TEXT"),
    ("ordersitems", "wikiLink", "VARCHAR(500)"),
    # ── rivenitems：对齐 Riven Item 模型 ──
    ("rivenitems", "enName", "VARCHAR(255)"),
    ("rivenitems", "subIcon", "VARCHAR(500)"),
    ("rivenitems", "wikiLink", "VARCHAR(500)"),
    # ── lichsisterweapons：对齐 Lich/Sister Weapon 模型 ──
    ("lichsisterweapons", "enName", "VARCHAR(255)"),
    ("lichsisterweapons", "wikiLink", "VARCHAR(500)"),
)

_COLUMN_RENAMES: tuple[tuple[str, str, str], ...] = (
    # (表, 旧列名, 新列名) — 与 API 字段名对齐
    ("rivention", "units", "unit"),
)


async def _apply_schema_upgrades() -> None:
    """给已存在的库补列。

    ``Tortoise.generate_schemas()`` 只建缺失的表，不会 ALTER 已有表，
    所以模型新增字段后旧库会缺列。这里按需补列，幂等。
    """
    conn = connections.get("default")
    for table, column, ddl in _SCHEMA_UPGRADES:
        try:
            rows = await conn.execute_query_dict(f"PRAGMA table_info({table})")
        except Exception as exc:  # 表不存在等情况交给后续建表
            logger.debug(f"检查表 {table} 结构失败: {exc}")
            continue
        if not rows:
            continue
        if column in {row.get("name") for row in rows}:
            continue
        try:
            await conn.execute_script(
                f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"
            )
            logger.info(f"数据库升级：{table} 表新增 {column} 列")
        except Exception as exc:
            logger.warning(f"给 {table} 补列 {column} 失败: {exc}")

    # 列改名（与 API 字段名对齐）；SQLite 3.25+ 支持 RENAME COLUMN
    for table, old_name, new_name in _COLUMN_RENAMES:
        try:
            rows = await conn.execute_query_dict(f"PRAGMA table_info({table})")
        except Exception:
            continue
        columns = {row.get("name") for row in rows}
        if not rows or old_name not in columns or new_name in columns:
            continue
        try:
            await conn.execute_script(
                f"ALTER TABLE {table} RENAME COLUMN {old_name} TO {new_name}"
            )
            logger.info(f"数据库升级：{table} 表 {old_name} 列改名为 {new_name}")
        except Exception as exc:
            logger.warning(f"重命名 {table}.{old_name} 失败: {exc}")


# ============================================================
# Tortoise ORM 模型模块路径
#
# AstrBot 以完全限定包名加载插件（如 data.plugins.astrbot_plugin_nyxbot），
# 因此从 __name__ 可以动态推导出完整的模型模块路径。
#
# 示例：
#   __name__ = "data.plugins.astrbot_plugin_nyxbot.src.init.engine"
#   ↓ rsplit(".", 2)[0] + ".model"
#   = "data.plugins.astrbot_plugin_nyxbot.src.model"
#
# 这样 Tortoise ORM 使用 importlib.import_module() 导入的模块，
# 与插件自身相对导入的模块在 sys.modules 中拥有相同的 key，
# 从而彻底避免"双模块冲突"问题。
# ============================================================
_MODEL_MODULE = __name__.rsplit(".", 2)[0] + ".model"
_MODELS_MODULES = [_MODEL_MODULE]

_tortoise_initialized: bool = False
_engine_lock: asyncio.Lock | None = None


async def get_engine():
    """初始化 Tortoise ORM 并建表（单例）。

    Tortoise ORM 使用 contextvars.ContextVar 存储连接上下文，
    仅 Tortoise.init() 所在的 asyncio task 中可用。
    Quart web API handler 运行在不同 task 中，context 不可用。

    通过 set_global_context() 将连接上下文设为全局回退，
    确保所有 asyncio task 都能通过 require_context() 获取连接。
    这是 Tortoise 官方为 FastAPI lifespan 跨 task 场景设计的 API。
    """
    global _tortoise_initialized, _engine_lock

    _db_path: str = str(Path(get_public_data_path()) / "nyxbot.db")
    logger.debug(f"数据库路径: {_db_path}")
    if not _tortoise_initialized:
        if _engine_lock is None:
            _engine_lock = asyncio.Lock()
        async with _engine_lock:
            if not _tortoise_initialized:
                # 根据配置开关控制 Tortoise ORM 的 SQL 日志输出
                if get_db_debug():
                    logging.getLogger("tortoise.db_client").setLevel(logging.DEBUG)
                    logging.getLogger("tortoise").setLevel(logging.DEBUG)
                    logger.info("数据库调试模式已启用")
                else:
                    logging.getLogger("tortoise.db_client").setLevel(logging.INFO)
                    logging.getLogger("tortoise").setLevel(logging.INFO)

                db_url = f"sqlite://{_db_path}"
                await Tortoise.init(
                    db_url=db_url,
                    modules={"models": _MODELS_MODULES},
                )
                await Tortoise.generate_schemas()
                await _apply_schema_upgrades()

                # 将 TortoiseContext 设为全局回退，使跨 asyncio task 均可访问
                # 若其他插件已设置全局回退，则跳过（NyxBot 的 contextvars 仍会在子 task 中传播）
                ctx = get_current_context()
                if ctx is not None:
                    try:
                        set_global_context(ctx)
                        logger.debug("TortoiseContext 已设为全局回退（跨 task 可用）")
                    except ConfigurationError:
                        logger.warning(
                            "无法设置全局 TortoiseContext 回退（已被其他插件占用），"
                            "NyxBot 数据库操作仅在当前 asyncio task 树中可用"
                        )

                _tortoise_initialized = True

    return Tortoise.get_connection("default")


async def close_engine() -> None:
    """关闭 TortoiseORM 连接。"""
    global _tortoise_initialized
    if _tortoise_initialized:
        await Tortoise.close_connections()
        _tortoise_initialized = False
        logger.info("TortoiseORM connections closed")
