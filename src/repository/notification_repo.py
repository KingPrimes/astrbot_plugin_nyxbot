"""Notification repository / 通知历史数据访问层"""
from __future__ import annotations

from typing import Optional

from tortoise.exceptions import DoesNotExist

from ..model.notification import NotificationHistory
from .base import BaseRepository


class NotificationRepository(BaseRepository[NotificationHistory]):
    """通知历史数据访问对象。"""

    def __init__(self):
        super().__init__(NotificationHistory)

    async def find_by_mission_id(
        self, mission_id: str
    ) -> Optional[NotificationHistory]:
        """根据任务 ID 查找通知记录。"""
        try:
            return await NotificationHistory.get(mission_id=mission_id)
        except DoesNotExist:
            return None

    async def find_by_mission_type(
        self, mission_type: str, limit: int = 50
    ) -> list[NotificationHistory]:
        """根据任务类型查找通知记录。"""
        return await NotificationHistory.filter(mission_type=mission_type).limit(limit)

    async def delete_older_than(self, cutoff_time: str) -> int:
        """删除早于指定时间的通知记录。"""
        deleted = await NotificationHistory.filter(notified_at__lt=cutoff_time).delete()
        return deleted

    async def count_by_type(self) -> dict[str, int]:
        """统计各类型的通知数量。"""
        result: dict[str, int] = {}
        all_records = await NotificationHistory.all().values_list("mission_type", flat=True)
        for mt in all_records:
            if mt:
                result[mt] = result.get(mt, 0) + 1
        return result


# 模块级单例
notification_repo = NotificationRepository()
