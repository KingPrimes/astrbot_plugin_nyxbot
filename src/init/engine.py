"""
Tortoise ORM Engine Lifecycle / Tortoise ORM 引擎生命周期

提供数据库引擎的单例初始化、关闭，以及初始化完成信号量。
从 data_sources_init.py 中抽离，消除 service 层对 init 层的循环依赖。
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import re
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
    # ── statetranslation：倒序路径索引列（把后缀匹配从全表扫变成索引范围查询）──
    ("statetranslation", "suffix", "VARCHAR(512)"),
    # ── weapons：对齐 ExportWeapons 的全部字段（近战震地/重击/滑行/范围等）──
    ("weapons", "slamAttack", "INTEGER"),
    ("weapons", "slamRadialDamage", "INTEGER"),
    ("weapons", "slamRadius", "INTEGER"),
    ("weapons", "heavyAttackDamage", "INTEGER"),
    ("weapons", "heavySlamAttack", "INTEGER"),
    ("weapons", "heavySlamRadialDamage", "INTEGER"),
    ("weapons", "heavySlamRadius", "INTEGER"),
    ("weapons", "slideAttack", "INTEGER"),
    ("weapons", "comboDuration", "INTEGER"),
    ("weapons", "range", "REAL"),
    ("weapons", "followThrough", "REAL"),
    ("weapons", "windUp", "REAL"),
    ("weapons", "blockingAngle", "INTEGER"),
    ("weapons", "excludeFromCodex", "INTEGER"),
    # ── warframes：对齐 ExportWarframes 的全部字段 ──
    ("warframes", "passiveDescription", "TEXT"),
    ("warframes", "longDescription", "TEXT"),
    ("warframes", "exalted", "TEXT"),
    ("warframes", "excludeFromCodex", "INTEGER"),
)

_COLUMN_RENAMES: tuple[tuple[str, str, str], ...] = (
    # (表, 旧列名, 新列名) — 与 API 字段名对齐
    ("rivention", "units", "unit"),
)


def _ident(name: str) -> str:
    """校验并原样返回 SQL 标识符（表名 / 列名）。

    这些值当前全部来自本文件顶部的硬编码常量，不存在注入面；但
    ``PRAGMA table_info({table})`` / ``DROP TABLE {table}`` /
    ``ALTER TABLE ... ADD COLUMN {column}`` 是本仓库唯一一处
    「拼接标识符执行 DDL」的地方——一旦以后有人把配置或外部输入接进来，
    没有这道闸就是注入点。

    Raises:
        ValueError: 标识符不符合 ``[A-Za-z_][A-Za-z0-9_]*``。
    """
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"非法的 SQL 标识符: {name!r}")
    return name


async def _drop_incompatible_tables() -> None:
    """丢弃结构与当前模型不兼容的表，交给 ``generate_schemas()`` 重建。

    ``generate_schemas()`` 只建缺失的表，不会修改已存在表的结构。主键定义
    变化时（``warframeability`` 从 ``abilityUniqueName`` 改为自增 ``id``）只能
    先删表重建。这里只处理「数据完全来自导出文件、可重新生成」的表。
    """
    conn = connections.get("default")
    checks: tuple[tuple[str, str, str], ...] = (
        # (表名, 新结构必须存在的列, 变更原因)
        ("warframeability", "id", "主键改为自增 id，以承载同一技能属于多个战甲"),
    )
    for table, required, reason in checks:
        try:
            rows = await conn.execute_query_dict(f"PRAGMA table_info({_ident(table)})")
        except Exception as exc:
            logger.debug(f"检查表 {table} 结构失败: {exc}")
            continue
        if not rows:
            continue  # 表不存在，交给 generate_schemas 新建
        if required in {row.get("name") for row in rows}:
            continue
        try:
            counted = await conn.execute_query_dict(
                f"SELECT COUNT(*) AS n FROM {_ident(table)}"
            )
            row_count = int(counted[0]["n"]) if counted else 0
        except Exception:
            row_count = 0
        if row_count:
            logger.warning(
                f"{table} 结构过旧（{reason}），重建会丢弃 {row_count} 行旧数据"
            )
        try:
            await conn.execute_script(f"DROP TABLE {_ident(table)}")
            logger.info(f"数据库结构升级：{table} 结构过旧（{reason}），已删除待重建")
        except Exception as exc:
            logger.warning(f"删除旧表 {table} 失败: {exc}")


async def _apply_schema_upgrades() -> None:
    """给已存在的库补列。

    ``Tortoise.generate_schemas()`` 只建缺失的表，不会 ALTER 已有表，
    所以模型新增字段后旧库会缺列。这里按需补列，幂等。

    Raises:
        RuntimeError: 有必补的列没建成。此时 ORM 已指向缺列的旧表，
            后续所有触碰到新列的查询都会失败——宁可启动失败让插件
            停用、下次启动重试，也不要带着「缺列但已就绪」的假状态跑。
    """
    conn = connections.get("default")
    failed: list[str] = []
    for table, column, ddl in _SCHEMA_UPGRADES:
        try:
            rows = await conn.execute_query_dict(f"PRAGMA table_info({_ident(table)})")
        except Exception as exc:  # 表不存在等情况交给后续建表
            logger.debug(f"检查表 {table} 结构失败: {exc}")
            continue
        if not rows:
            continue
        if column in {row.get("name") for row in rows}:
            continue
        try:
            await conn.execute_script(
                f"ALTER TABLE {_ident(table)} ADD COLUMN {_ident(column)} {ddl}"
            )
            logger.info(f"数据库升级：{table} 表新增 {column} 列")
        except Exception as exc:
            # 库被短暂锁住 / 不可写时会走到这里。不能只 warn 后继续——
            # 那样 ORM 会被标记为已初始化，裂罅分析等查询到新列时才炸。
            logger.error(f"给 {table} 补列 {column} 失败: {exc}")
            failed.append(f"{table}.{column}")

    # 列改名（与 API 字段名对齐）；SQLite 3.25+ 支持 RENAME COLUMN
    for table, old_name, new_name in _COLUMN_RENAMES:
        try:
            rows = await conn.execute_query_dict(f"PRAGMA table_info({_ident(table)})")
        except Exception:
            continue
        columns = {row.get("name") for row in rows}
        if not rows or old_name not in columns or new_name in columns:
            continue
        try:
            await conn.execute_script(
                f"ALTER TABLE {_ident(table)} RENAME COLUMN "
                f"{_ident(old_name)} TO {_ident(new_name)}"
            )
            logger.info(f"数据库升级：{table} 表 {old_name} 列改名为 {new_name}")
        except Exception as exc:
            logger.error(f"重命名 {table}.{old_name} 失败: {exc}")
            failed.append(f"{table}.{old_name}→{new_name}")

    if failed:
        raise RuntimeError(
            f"数据库结构升级失败（{len(failed)} 项：{', '.join(failed)}），"
            "插件将在下次启动重试；请检查数据库文件是否被占用或只读"
        )

    # ``Tortoise.generate_schemas()`` 用双引号包标识符。旧库还缺 ``suffix``
    # 列时，SQLite 的 DQS 会把 ``"suffix"`` 当字符串字面量，于是建出一个
    # **建在常量上的索引**（``PRAGMA index_info`` → ``(0, -2, None)``）而不报
    # 错；``ALTER TABLE ADD COLUMN`` 之后该索引被重新解析成正常的 suffix 索引，
    # 但已有行没有索引项（``PRAGMA integrity_check`` 报
    # "row N missing from index"），走索引的查询会静默漏行。
    #
    # 修复顺序不能改：先删索引 → 再回填 → 最后建索引。门控用 ``NOT INDEXED``
    # 的统计而不是 ``filter(suffix=None)``：坏索引存在时后者会走索引返回 0，
    # 正好掩盖要修的问题（见 ``_count_state_translation_missing_suffix``）。
    pending = await _count_state_translation_missing_suffix()
    if pending:
        logger.info(f"数据库升级：statetranslation.suffix 待回填 {pending} 行")
        await _drop_state_translation_index()
        await _backfill_state_translation_suffix()
        await _ensure_state_translation_index()
        if remaining := await _count_state_translation_missing_suffix():
            logger.warning(
                f"statetranslation.suffix 仍有 {remaining} 行为空，"
                "这些条目的后缀翻译会漏"
            )


_STATE_TRANSLATION_SUFFIX_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_statetranslation_suffix "
    "ON statetranslation(suffix)"
)
"""``statetranslation.suffix`` 的索引；新库由模型 Meta 建，旧库在这里补。"""

_STATE_TRANSLATION_BACKFILL_BATCH = 300
"""回填时分批提交，避免一次性构造上万实例。

``bulk_update`` 每行产生 3 个参数（PK + 值 + IN 列表），300 行 ≈ 900 个，
保守地留在 SQLite 常见 999 参数上限内。
"""


async def _count_state_translation_missing_suffix() -> int:
    """统计 ``suffix`` 仍为 NULL 的行数（对坏索引免疫）。

    必须带 ``NOT INDEXED``：坏索引存在时 ``WHERE suffix IS NULL`` 会走索引并
    返回 0，导致「看起来已经回填完」——这正是要绕开的假象。

    Returns:
        待回填行数；表尚不可用（新库首次启动等）时返回 0，交给后续启动处理。
    """
    conn = connections.get("default")
    try:
        rows = await conn.execute_query_dict(
            "SELECT COUNT(*) AS pending FROM statetranslation NOT INDEXED "
            "WHERE suffix IS NULL"
        )
    except Exception as exc:  # 表还没建好时交给后续建表
        logger.debug(f"统计待回填的 statetranslation 失败: {exc}")
        return 0
    return int(rows[0]["pending"]) if rows else 0


async def _drop_state_translation_index() -> None:
    """删除 ``statetranslation.suffix`` 索引（幂等）。

    必须在补列之后、回填之前调用：``generate_schemas()`` 可能在旧库上
    建出一个引用尚不存在列的**空索引**（SQLite 允许这样建），留着它会让
    ``suffix IS NULL`` 这类查询走索引而漏掉全部行。
    """
    conn = connections.get("default")
    try:
        await conn.execute_script("DROP INDEX IF EXISTS idx_statetranslation_suffix")
    except Exception as exc:
        logger.warning(f"删除 statetranslation.suffix 索引失败: {exc}")


async def _ensure_state_translation_index() -> None:
    """确保 ``statetranslation.suffix`` 索引存在且与数据一致（幂等）。"""
    conn = connections.get("default")
    try:
        await conn.execute_script(_STATE_TRANSLATION_SUFFIX_INDEX)
    except Exception as exc:  # 表还没建好时交给后续建表
        logger.warning(f"创建 statetranslation.suffix 索引失败: {exc}")


async def _backfill_state_translation_suffix() -> None:
    """给旧库回填 ``statetranslation.suffix``（只处理 NULL，幂等）。

    新库由 ``StateTranslationService.sync_data`` 在 ``build_instance``
    里直接写入；从旧版本升级上来的库里该列是 NULL，后缀查询会全部漏掉，
    这里在启动时补一次。
    """
    # 局部导入：engine 是基础设施层，不在导入期依赖具体模型包
    from ..model.state_translation import StateTranslation
    from ..util.string_utils import suffix_index_key

    try:
        rows = await StateTranslation.filter(suffix=None).only("uniqueName")
    except Exception as exc:
        logger.warning(f"查询待回填的 statetranslation 失败: {exc}")
        return
    if not rows:
        return

    for row in rows:
        row.suffix = suffix_index_key(row.uniqueName)
    try:
        await StateTranslation.bulk_update(
            rows, fields=["suffix"], batch_size=_STATE_TRANSLATION_BACKFILL_BATCH
        )
        logger.info(f"数据库升级：回填 statetranslation.suffix {len(rows)} 行")
    except Exception as exc:
        logger.warning(f"回填 statetranslation.suffix 失败: {exc}")


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

    # SQLite 不会创建目录，缺目录时只报 "unable to open database file"，
    # 看不出是路径问题。这里与其它写入点（export_downloader / arbitration /
    # settings）保持一致，打开库之前先确保数据目录存在——不能只依赖
    # ``get_public_data_path()`` 里 ``StarTools.get_data_dir()`` 的建目录副作用，
    # 它被进程内缓存包着，目录被删（用户清理、迁移、重装）之后不会再触发。
    _data_dir = Path(get_public_data_path())
    _data_dir.mkdir(parents=True, exist_ok=True)
    _db_path: str = str(_data_dir / "nyxbot.db")
    logger.debug(f"数据库路径: {_db_path}")
    if not _tortoise_initialized:
        if _engine_lock is None:
            _engine_lock = asyncio.Lock()
        async with _engine_lock:
            if not _tortoise_initialized:
                # 根据配置开关控制 Tortoise ORM 的 SQL 日志输出。
                # 注意：这里的 logging.getLogger 调的是**框架/第三方库**的 logger
                #（tortoise 自身走标准 logging 体系），只调整其级别，不用于本插件
                # 输出日志；插件自身的日志一律走 astrbot.api.logger。
                if get_db_debug():
                    logging.getLogger("tortoise.db_client").setLevel(logging.DEBUG)
                    logging.getLogger("tortoise").setLevel(logging.DEBUG)
                    logger.info("数据库调试模式已启用")
                else:
                    logging.getLogger("tortoise.db_client").setLevel(logging.INFO)
                    logging.getLogger("tortoise").setLevel(logging.INFO)

                db_url = f"sqlite://{_db_path}"
                try:
                    await Tortoise.init(
                        db_url=db_url,
                        modules={"models": _MODELS_MODULES},
                    )
                    await _drop_incompatible_tables()
                    await Tortoise.generate_schemas()
                    # 结构升级失败会在这里抛错。必须先把连接关掉再往外抛，
                    # 否则 Tortoise 处于「已 init 但缺列」的半初始化状态，
                    # `_tortoise_initialized` 保持 False 的下一次尝试会
                    # 撞上「重复 init」而无法从干净状态重试。
                    await _apply_schema_upgrades()
                except Exception:
                    with contextlib.suppress(Exception):
                        await Tortoise.close_connections()
                    raise

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
