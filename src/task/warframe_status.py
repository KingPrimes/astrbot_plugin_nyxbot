"""Warframe Status Task / 定时拉取 WorldState 任务

定时从 Warframe API 拉取世界状态数据，检测变更并触发通知。
"""
from __future__ import annotations

import asyncio
from typing import Optional

from astrbot.api import logger

from ..config import get_wf_update_interval


class WarframeStatusTask:
    """定时拉取 WorldState 并触发通知。

    使用 asyncio 循环定时拉取 Warframe 世界状态数据。
    """

    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """启动定时任务。"""
        if self._running:
            logger.warning("WorldState 定时任务已在运行")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("WorldState 定时任务已启动")

    async def stop(self):
        """停止定时任务。"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("WorldState 定时任务已停止")

    @property
    def is_running(self) -> bool:
        """是否正在运行。"""
        return self._running

    async def _run_loop(self):
        """主循环。"""
        interval = get_wf_update_interval()

        while self._running:
            try:
                await self._fetch_and_notify()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"WorldState 拉取失败: {e}")

            await asyncio.sleep(interval)

    async def _fetch_and_notify(self):
        """拉取并推送变更通知。

        1. 拉取 WorldState 数据
        2. 检测变更
        3. 推送通知给订阅用户
        """
        from ..api import WorldStateClient
        from ..service.detector import (
            AlertsChangeDetector,
            FissuresChangeDetector,
            InvasionsChangeDetector,
        )
        from ..service.notification import NotificationService

        # 检测各类型变更
        detectors = [
            ("alerts", AlertsChangeDetector()),
            ("fissures", FissuresChangeDetector()),
            ("invasions", InvasionsChangeDetector()),
        ]

        for mission_type, detector in detectors:
            try:
                changes = await detector.detect_changes()
                for change in changes:
                    # 检查是否已通知
                    change_id = str(change.get("id", change.get("_id", "")))
                    if change_id and await NotificationService.has_notified(change_id):
                        continue

                    # 记录通知
                    await NotificationService.record_notification(
                        mission_type=mission_type,
                        mission_id=change_id,
                        title=f"新的{mission_type}任务",
                        content=str(change),
                    )
                    logger.info(f"检测到新的 {mission_type}: {change_id}")
            except Exception as e:
                logger.error(f"检测 {mission_type} 变更失败: {e}")
