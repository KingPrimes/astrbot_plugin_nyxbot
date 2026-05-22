"""Relics service / 遗物服务

提供遗物（Relics）的数据同步和查询功能。
当前为 stub，待后续实现。
"""
from __future__ import annotations

from astrbot.api import logger


class RelicsService:
    """遗物服务（stub — 待实现）。"""

    @classmethod
    async def sync_data(cls) -> None:
        """初始化 Relics（遗物）表数据（含关联的 RelicRewards）。"""
        logger.info("初始化遗物数据 (stub) — 待实现")
