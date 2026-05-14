"""Notification service / 通知服务

管理通知的发送和历史记录。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ..model.notification import NotificationHistory


class NotificationService:
    """通知服务：发送通知、记录历史。"""

    @classmethod
    async def record_notification(
        cls,
        mission_type: str,
        mission_id: str,
        title: str = "",
        content: str = "",
        notified_users: str = "",
    ) -> NotificationHistory:
        """记录通知历史。

        Args:
            mission_type: 任务类型。
            mission_id: 任务唯一 ID。
            title: 通知标题。
            content: 通知内容。
            notified_users: 已通知的用户 ID 列表（逗号分隔）。

        Returns:
            创建的通知历史记录。
        """
        ...

    @classmethod
    async def has_notified(cls, mission_id: str) -> bool:
        """检查是否已通知过指定任务。

        Args:
            mission_id: 任务唯一 ID。

        Returns:
            是否已通知。
        """
        ...

    @classmethod
    async def clean_old_records(cls, retention_hours: int = 12) -> int:
        """清理超过保留时长的通知记录。

        Args:
            retention_hours: 保留时长（小时）。

        Returns:
            清理的记录数。
        """
        ...

    @classmethod
    async def get_history(
        cls,
        mission_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ):
        """获取通知历史。

        Args:
            mission_type: 可选的任务类型过滤。
            page: 页码。
            page_size: 每页大小。

        Returns:
            (记录列表, 总记录数) 的元组。
        """
        ...
