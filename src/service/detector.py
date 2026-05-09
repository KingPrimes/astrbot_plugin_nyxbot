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
        current = await self.fetch_current()
        if self._previous_state is None:
            self._previous_state = current
            return []

        changes = self._compute_changes(self._previous_state, current)
        self._previous_state = current
        return changes

    def _compute_changes(
        self,
        old: dict[str, Any],
        new: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """计算差异（子类可重写）。

        默认实现：按所有键名对比每个键下的条目 ID。
        """
        changes = []
        for key in new:
            old_items = old.get(key, [])
            new_items = new.get(key, [])

            if not isinstance(old_items, list) or not isinstance(new_items, list):
                continue

            old_ids = {self._get_item_id(item) for item in old_items}
            for item in new_items:
                item_id = self._get_item_id(item)
                if item_id and item_id not in old_ids:
                    changes.append(item)

        return changes

    @staticmethod
    def _get_item_id(item: Any) -> Optional[str]:
        """从条目中获取唯一 ID。"""
        if isinstance(item, dict):
            return item.get("id", item.get("_id", item.get("Id", "")))
        return None


class AlertsChangeDetector(BaseChangeDetector):
    """警报变更检测器。"""

    async def fetch_current(self) -> dict[str, Any]:
        from ..api import WorldStateClient

        raw = await WorldStateClient.fetch_raw()
        return {"Alerts": raw.get("Alerts", []) if raw else []}


class FissuresChangeDetector(BaseChangeDetector):
    """裂隙变更检测器。"""

    async def fetch_current(self) -> dict[str, Any]:
        from ..api import WorldStateClient

        raw = await WorldStateClient.fetch_raw()
        return {"Fissures": raw.get("Fissures", []) if raw else []}


class InvasionsChangeDetector(BaseChangeDetector):
    """入侵变更检测器。"""

    async def fetch_current(self) -> dict[str, Any]:
        from ..api import WorldStateClient

        raw = await WorldStateClient.fetch_raw()
        return {"Invasions": raw.get("Invasions", []) if raw else []}
