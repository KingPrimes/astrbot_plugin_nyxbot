"""Notification service / 通知服务

管理通知的发送和历史记录。
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

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
        notified_users: list[str] | None = None,
    ) -> NotificationHistory:
        """记录通知历史。

        Args:
            mission_type: 任务类型。
            mission_id: 任务唯一 ID。
            title: 通知标题。
            content: 通知内容。
            notified_users: 已通知的用户 ID 列表。

        Returns:
            创建的通知历史记录。
        """
        instance = NotificationHistory(
            mission_type=mission_type,
            mission_id=mission_id,
            title=title,
            content=content,
            notified_users=notified_users or [],
            notified_at=int(time.time()),
        )
        await instance.save()
        return instance

    @classmethod
    async def has_notified(cls, mission_id: str) -> bool:
        """检查是否已通知过指定任务。

        Args:
            mission_id: 任务唯一 ID。

        Returns:
            是否已通知。
        """
        from tortoise.exceptions import DoesNotExist
        try:
            await NotificationHistory.get(mission_id=mission_id)
            return True
        except DoesNotExist:
            return False

    @classmethod
    async def clean_old_records(cls, retention_hours: int = 12) -> int:
        """清理超过保留时长的通知记录。

        Args:
            retention_hours: 保留时长（小时）。

        Returns:
            清理的记录数。
        """
        cutoff = int(
            (datetime.now(timezone.utc) - timedelta(hours=retention_hours)).timestamp()
        )
        deleted = await NotificationHistory.filter(notified_at__lt=cutoff).delete()
        return deleted

    @classmethod
    async def get_history(
        cls,
        mission_type: str | None = None,
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
        offset = (page - 1) * page_size
        qs = NotificationHistory.all()
        if mission_type:
            qs = qs.filter(mission_type=mission_type)
        total = await qs.count()
        items = await qs.order_by("-notified_at").offset(offset).limit(page_size)
        return list(items), total
