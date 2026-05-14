"""Change Detector / 变更检测器

检测 WorldState 数据的变化，用于触发通知。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseChangeDetector(ABC):
    """变更检测器基类。

    检测 Warframe WorldState 数据的变化，返回新增或变更的条目。
    """

    def __init__(self):
        self._previous_state: dict[str, Any] | None = None

    @abstractmethod
    async def fetch_current(self) -> dict[str, Any]:
        """获取当前状态。

        Returns:
            当前状态的原始数据。
        """

    async def detect_changes(self) -> list[dict[str, Any]]:
        """检测变化，返回新增或变更的条目。

        Returns:
            新增或变更的条目列表。
        """
        ...

    def _compute_changes(
        self,
        old: dict[str, Any],
        new: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """计算差异（子类可重写）。

        默认实现：按所有键名对比每个键下的条目 ID。
        """
        ...

    @staticmethod
    def _get_item_id(item: Any) -> Optional[str]:
        """从条目中获取唯一 ID。"""
        ...


class AlertsChangeDetector(BaseChangeDetector):
    """警报变更检测器。"""

    async def fetch_current(self) -> dict[str, Any]:
        ...


class FissuresChangeDetector(BaseChangeDetector):
    """裂隙变更检测器。"""

    async def fetch_current(self) -> dict[str, Any]:
        ...


class InvasionsChangeDetector(BaseChangeDetector):
    """入侵变更检测器。"""

    async def fetch_current(self) -> dict[str, Any]:
        ...
