"""游戏版本跟踪 / Game build label tracking

``worldState.php`` 里的 ``BuildLabel``（形如 ``2026.10.28.09.54/8e7dGXr3...``）
就是游戏版本号。WorldState 本身在按 TTL 轮询，本模块挂在轮询成功之后：

    BuildLabel 与本地记录不同 → 判定为游戏更新 → 后台刷新官方导出文件
    以及依赖它们的数据表（状态翻译 / 星图节点 / 电波 / 武器 / 遗物）。

为什么用 BuildLabel 而不是定时刷新：导出文件动辄几十 MB，只在游戏真正更新时
才需要重下；而 WorldState 的轮询本来就在跑，等于免费拿到版本信号。

状态文件：``<插件数据目录>/game_build_label.json``
"""
from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from astrbot.api import logger

from ..util.data_path import get_public_data_path

STATE_FILE_NAME = "game_build_label.json"

_task: asyncio.Task | None = None
"""后台刷新任务（同一时刻只允许一个）。"""


def _state_path() -> Path:
    return Path(get_public_data_path()) / STATE_FILE_NAME


def read_build_label() -> str:
    """读取本地记录的 BuildLabel；缺失或损坏返回空串。"""
    try:
        raw = _state_path().read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    except OSError as exc:
        logger.debug(f"读取游戏版本状态失败: {exc}")
        return ""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return ""
    return str(data.get("label") or "") if isinstance(data, dict) else ""


def write_build_label(label: str) -> None:
    """记录已应用的 BuildLabel。"""
    if not label:
        return
    payload = {"label": label, "updated_at": int(time.time())}
    try:
        _state_path().write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError as exc:
        logger.warning(f"写入游戏版本状态失败: {exc}")


async def on_build_label(label: str) -> None:
    """WorldState 拉到 BuildLabel 后调用：变化则触发后台刷新导出数据。"""
    if not label:
        return

    stored = read_build_label()
    if not stored:
        # 首次记录：bootstrap 已经导过数据，这里只落标记
        write_build_label(label)
        logger.info(f"记录游戏版本: {label}")
        return
    if stored == label:
        return

    from ..config import DATA_INIT_MODE_NEVER, DATA_INIT_MODE_OFFLINE, get_data_init_mode

    if get_data_init_mode() in (DATA_INIT_MODE_NEVER, DATA_INIT_MODE_OFFLINE):
        logger.info(
            f"检测到游戏版本更新 {stored} → {label}，"
            f"但当前模式跳过联网刷新（导出数据保持原样）"
        )
        return

    global _task
    if _task and not _task.done():
        logger.info(f"检测到游戏版本更新 {stored} → {label}，刷新任务已在执行中")
        return

    logger.info(f"检测到游戏版本更新 {stored} → {label}，后台刷新导出数据")
    _task = asyncio.create_task(_refresh_export_data(label))


async def _run_stage(name: str, func: Callable[[], Awaitable[object]]) -> bool:
    """执行单个同步阶段，异常只记录不中断。

    部分 ``sync_data()`` 用返回值表达失败（导出文件下载失败返回 ``False``），
    必须检查返回值，否则失败会被当成成功并写入新的 BuildLabel，导致永不重试。
    """
    try:
        result = await func()
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.error(f"游戏版本更新后同步失败：{name} — {exc}", exc_info=True)
        return False

    if result is False:
        logger.error(f"游戏版本更新后同步失败：{name} — 返回 False")
        return False
    return True


async def _refresh_export_data(label: str) -> None:
    """刷新官方导出文件及其派生数据表。

    导出文件本身有 hash 比对，只会下载真正变化的文件；这里按依赖顺序串行执行，
    避免「翻译还没更新，武器名先查不到」的中间态。
    """
    from ..service import (
        NightWaveService,
        NodesService,
        RelicsService,
        StateTranslationService,
        WeaponsService,
    )

    started = time.monotonic()
    stages: list[tuple[str, Callable[[], Awaitable[object]]]] = [
        # 状态翻译内部会先调 sever_export_files() 下载导出文件
        ("状态翻译 / 导出文件", StateTranslationService.sync_data),
        ("星图节点", NodesService.sync_data),
        ("电波任务", NightWaveService.sync_data),
        ("武器", WeaponsService.sync_data),
        ("遗物", RelicsService.sync_data),
    ]

    failed = [name for name, func in stages if not await _run_stage(name, func)]

    if failed:
        logger.warning(
            f"游戏版本更新同步未全部成功（{', '.join(failed)}），"
            "版本标记暂不更新，下轮轮询会重试"
        )
        return

    write_build_label(label)
    logger.info(
        f"游戏版本 {label} 的导出数据刷新完成，耗时 {time.monotonic() - started:.1f}s"
    )
