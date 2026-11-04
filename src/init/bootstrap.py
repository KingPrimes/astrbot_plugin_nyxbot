"""Data bootstrap / 数据初始化编排

按插件配置 `wf_data_init_mode` 决定启动时是否导入数据：

| 模式 | 启动数据导入 | OCR / 仲裁预热 / WorldState |
| --- | --- | --- |
| `auto`（默认） | 核心表缺数据才导入；已导入过则跳过 | 正常启动 |
| `always` | 忽略非空判断，每次启动重跑全量导入 | 正常启动 |
| `never` | 跳过，直接使用现有数据库（开发调试） | 正常启动 |
| `offline` | 跳过 | 一并跳过（离线 / CI） |

旧配置（`wf_runtime_env` + `wf_data_force_sync`）会在读取时自动映射到上述模式。
"""
from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable

from tortoise import Tortoise

from astrbot.api import logger

from ..api.cdn_client import CdnClient
from ..config import (
    DATA_INIT_MODE_ALWAYS,
    DATA_INIT_MODE_NEVER,
    DATA_INIT_MODE_OFFLINE,
    get_data_init_mode,
    normalize_data_init_mode,
)
from ..util.search_index import invalidate as invalidate_search_index
from ..util.search_index import start_prewarm as start_index_prewarm
from .data_version import UpdatePlan, plan_update, write_state
from .engine import get_engine

# 判断「数据是否已初始化」的核心表：任一为空即视为需要导入
CORE_TABLES: tuple[str, ...] = (
    "statetranslation",
    "nodes",
    "weapons",
    "relics",
    "relicrewards",
    "rewardpool",
    "reward",
    "nightwave",
    "alias",
    "ordersitems",
)

SyncFunc = Callable[[], Awaitable[object]]


def is_offline_mode(mode: str | None = None) -> bool:
    """当前是否为 offline 模式（跳过 OCR 与后台网络任务）。"""
    return normalize_data_init_mode(mode or get_data_init_mode()) == DATA_INIT_MODE_OFFLINE


def allows_network(mode: str | None = None) -> bool:
    """当前模式是否允许后台联网刷新。

    ``never`` 与 ``offline`` 都只使用本地缓存，不产生远程请求；
    ``auto`` / ``always`` 允许刷新（仲裁仍会按缓存新鲜度决定是否真的拉取）。
    """
    return normalize_data_init_mode(mode or get_data_init_mode()) not in {
        DATA_INIT_MODE_NEVER,
        DATA_INIT_MODE_OFFLINE,
    }


def _iter_registered_models() -> list[type]:
    """取出 Tortoise 已注册的全部模型类（兼容 0.x dict 与 1.x Apps 两种结构）。"""
    registry = getattr(Tortoise, "apps", None)
    if registry is None:
        return []

    if isinstance(registry, dict):
        groups = list(registry.values())
    else:  # tortoise >= 1.0: Apps 对象
        groups = list(getattr(registry, "apps", {}).values())

    models: list[type] = []
    seen: set[int] = set()
    for group in groups:
        if not isinstance(group, dict):
            continue
        for model in group.values():
            if id(model) not in seen:
                seen.add(id(model))
                models.append(model)
    return models


async def table_counts() -> dict[str, int]:
    """统计 Tortoise 已注册模型对应表的行数。"""
    counts: dict[str, int] = {}
    for model in _iter_registered_models():
        table = model._meta.db_table
        try:
            counts[table] = await model.all().count()
        except Exception as exc:  # 表不存在等情况不影响整体判断
            logger.debug(f"统计表 {table} 行数失败: {exc}")
    return counts


async def missing_core_tables() -> list[str]:
    """返回仍为空的核心表名列表。"""
    counts = await table_counts()
    return [table for table in CORE_TABLES if counts.get(table, 0) == 0]


async def _run_stage(name: str, func: SyncFunc) -> bool:
    """执行单个同步阶段，异常只记录不中断。

    注意：部分 ``sync_data()`` 用返回值表达失败（如导出文件下载失败返回 ``False``），
    所以这里必须检查返回值，否则失败会被当成成功，进而写入版本标记导致永不重试。
    """
    try:
        result = await func()
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.error(f"数据同步失败：{name} — {exc}", exc_info=True)
        return False

    if result is False:
        logger.error(f"数据同步失败：{name} — 返回 False")
        return False
    return True


async def _import_all(plan: UpdatePlan) -> bool:
    """按更新计划执行数据导入。

    ``plan.full`` 为真时全量导入；否则只跑 ``plan.needs()`` 命中的数据集。
    非 DataSource 来源（warframe.market API、官方导出文件）只在全量时执行。

    Returns:
        True 表示所有执行的阶段都成功；False 表示有阶段失败（调用方不应写入版本标记）。
    """
    from ..service import (
        AliasService,
        ArbitrationService,
        MarketSyncService,
        NightWaveService,
        NodesService,
        RelicsService,
        RewardService,
        RivenService,
        SentinelsService,
        StateTranslationService,
        UpgradesService,
        WarframesService,
        WeaponsService,
    )

    started = time.monotonic()
    scope = "全量" if plan.full else "增量"
    logger.info(f"开始数据初始化（{scope}）...")

    failed: list[str] = []

    # 阶段 1：状态翻译（顺带下载官方导出文件）
    if plan.needs("state_translation.json"):
        if not await _run_stage(
            "状态翻译 / 导出文件", StateTranslationService.sync_data
        ):
            failed.append("状态翻译")
            logger.warning("导出文件不可用，依赖导出文件的数据可能为空")
    else:
        logger.debug("状态翻译数据未变化，跳过")

    # 阶段 2：互不依赖的数据源并发拉取
    parallel: list[tuple[str, SyncFunc]] = []

    if plan.needs("alias.json"):
        parallel.append(("别名", AliasService.sync_data))
    if plan.needs("market_riven_tion.json"):
        parallel.append(("紫卡倾向", RivenService.sync_tion_data))
    if plan.needs("market_riven_tion_alias.json"):
        parallel.append(("紫卡别名", RivenService.sync_tion_alias_data))
    if plan.needs("riven_analyse_trend.json"):
        parallel.append(("紫卡趋势", RivenService.sync_analyse_trend_data))
    if plan.needs("reward_pool.json"):
        parallel.append(("奖励池", RewardService.sync_data))
    if plan.needs("nodes.json"):
        parallel.append(("星图节点", NodesService.sync_data))
    if plan.needs("arbitration_tiers.json"):
        parallel.append(("仲裁分级", ArbitrationService.sync_tiers))

    # 以下来源不是 DataSource，只在全量导入时执行
    if plan.full:
        parallel += [
            ("紫卡物品", RivenService.sync_items_data),
            ("市场物品", MarketSyncService.sync_orders_items),
            ("幻纹", MarketSyncService.sync_ephemeras),
            ("赤毒/信条武器", MarketSyncService.sync_lich_sister_weapons),
            ("电波任务", NightWaveService.sync_data),
            ("武器", WeaponsService.sync_data),
        ]

    if parallel:
        results = await asyncio.gather(
            *(func() for _, func in parallel), return_exceptions=True
        )
        for (name, _), result in zip(parallel, results, strict=True):
            if isinstance(result, BaseException):
                logger.error(f"数据同步失败：{name} — {result}")
                failed.append(name)
            elif result is False:
                logger.error(f"数据同步失败：{name} — 返回 False")
                failed.append(name)

    # 阶段 3：依赖翻译/奖励数据的表，串行执行
    serial: list[tuple[str, SyncFunc]] = []
    if plan.full:
        serial += [
            ("遗物", RelicsService.sync_data),
            ("守护（stub）", SentinelsService.sync_data),
            ("MOD（stub）", UpgradesService.sync_data),
            ("战甲（stub）", WarframesService.sync_data),
        ]
    elif plan.needs("state_translation.json"):
        # 遗物奖励名在导入时按翻译表固化成中文（RelicsService._translate_relic_rewards），
        # 翻译更新后必须重跑，否则库里还是旧名字
        serial.append(("遗物", RelicsService.sync_data))

    for name, func in serial:
        if not await _run_stage(name, func):
            failed.append(name)

    logger.info(f"数据初始化完成，耗时 {time.monotonic() - started:.1f}s")
    if failed:
        logger.warning(
            f"以下阶段未成功：{', '.join(failed)}；本次不记录版本标记，下次启动会重试"
        )
        return False
    return True


async def bootstrap_data(mode: str | None = None) -> bool:
    """按数据初始化模式决定是否导入数据，完成后后台预热搜索索引。

    Args:
        mode: `auto` / `always` / `never` / `offline`；
            `None` 时读取配置 `wf_data_init_mode`。

    Returns:
        本次是否真正执行了导入。
    """
    imported = await _bootstrap_data(mode)
    # 数据已就绪（导入或跳过都算）：后台预热索引，不阻塞初始化流程
    start_index_prewarm()
    return imported


async def _bootstrap_data(mode: str | None) -> bool:
    """``bootstrap_data`` 的实现体：判断是否需要导入并执行。"""
    current = normalize_data_init_mode(mode or get_data_init_mode())

    await get_engine()
    counts = await table_counts()
    total_rows = sum(counts.values())
    empty = [table for table in CORE_TABLES if counts.get(table, 0) == 0]

    if current in (DATA_INIT_MODE_NEVER, DATA_INIT_MODE_OFFLINE):
        logger.info(
            f"数据初始化模式 {current}：跳过启动导入"
            f"（{len(counts)} 张表 / {total_rows} 行，空核心表 {len(empty)} 张）"
        )
        return False

    # always：忽略一切判断，强制全量
    if current == DATA_INIT_MODE_ALWAYS:
        logger.info("数据初始化模式 always：忽略非空判断，强制全量导入")
        plan = UpdatePlan(tag=await CdnClient.get_latest_tag(), changed=None)
        if await _import_all(plan):
            write_state(plan.tag)
        return await _report_result()

    # 核心表缺数据：必须全量补齐，但仍记录当前版本，避免下次重复全量
    if empty:
        logger.info(f"核心表缺数据：{', '.join(empty)}，开始全量导入")
        plan = UpdatePlan(tag=await CdnClient.get_latest_tag(), changed=None)
        if await _import_all(plan):
            write_state(plan.tag)
        return await _report_result()

    # 数据齐备：只看 DataSource 版本差异，按变化数据集增量导入
    plan = await plan_update()
    if plan.empty:
        logger.info(
            f"DataSource 版本未变（{plan.tag or '未知'}），跳过数据导入"
            f"（{len(counts)} 张表 / {total_rows} 行）"
        )
        return False

    logger.info(
        f"DataSource 有新版本 {plan.tag or '（未知）'}，仅更新变化的数据集"
        if not plan.full
        else "DataSource 需要全量同步"
    )
    if await _import_all(plan):
        write_state(plan.tag)
    return await _report_result()


async def _report_result() -> bool:
    """统计导入结果并打日志。"""
    counts = await table_counts()
    empty = [table for table in CORE_TABLES if counts.get(table, 0) == 0]
    logger.info(
        f"数据初始化结果：{len(counts)} 张表 / {sum(counts.values())} 行"
        + (f"，仍为空：{', '.join(empty)}" if empty else "")
    )
    # 数据变了，内存搜索索引需要重建
    invalidate_search_index()
    return True
