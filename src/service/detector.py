"""Change Detector / 变更检测器

检测 WorldState 数据的变化，用于触发通知。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .world_state import WorldStateService


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
        current = await self.fetch_current()
        if self._previous_state is None:
            self._previous_state = current
            return []  # 首次运行，不报告变更

        changes = self._compute_changes(self._previous_state, current)
        self._previous_state = current
        return changes

    def _compute_changes(
        self,
        old: dict[str, Any],
        new: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """计算差异（子类可重写）。

        默认实现：按所有键名对比每个键下的条目 ID，
        返回 new 中有但 old 中没有的条目。
        """
        changes: list[dict[str, Any]] = []
        all_keys = set(old.keys()) | set(new.keys())
        for key in all_keys:
            old_items = old.get(key, [])
            new_items = new.get(key, [])
            if not isinstance(old_items, list):
                old_items = []
            if not isinstance(new_items, list):
                new_items = []

            old_ids = {
                self._get_item_id(item)
                for item in old_items
                if self._get_item_id(item) is not None
            }
            for item in new_items:
                item_id = self._get_item_id(item)
                if item_id is not None and item_id not in old_ids:
                    changes.append({"_key": key, **item})
        return changes

    @staticmethod
    def _get_item_id(item: Any) -> str | None:
        """从条目中获取唯一 ID。"""
        if isinstance(item, dict):
            return str(item.get("id", item.get("_id", item.get("Id", ""))))
        return str(getattr(item, "id", None) or "")


class AlertsChangeDetector(BaseChangeDetector):
    """警报变更检测器。"""

    async def fetch_current(self) -> dict[str, Any]:
        alerts = await WorldStateService.get_alerts()
        return {"alerts": alerts}


class FissuresChangeDetector(BaseChangeDetector):
    """裂隙变更检测器。"""

    async def fetch_current(self) -> dict[str, Any]:
        fissures = await WorldStateService.get_fissures()
        return {"fissures": fissures}


class InvasionsChangeDetector(BaseChangeDetector):
    """入侵变更检测器。"""

    async def fetch_current(self) -> dict[str, Any]:
        invasions = await WorldStateService.get_invasions()
        return {"invasions": invasions}
