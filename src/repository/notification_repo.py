"""Notification repository / 通知历史数据访问层"""
from __future__ import annotations

from typing import Optional

from sqlmodel import select, func, delete as sql_delete
from sqlmodel.ext.asyncio.session import AsyncSession

from ..model.notification import NotificationHistory
from .base import BaseRepository


class NotificationRepository(BaseRepository[NotificationHistory]):
    """通知历史数据访问对象。"""

    def __init__(self):
        super().__init__(NotificationHistory)

    async def find_by_mission_id(
        self, session: AsyncSession, mission_id: str
    ) -> Optional[NotificationHistory]:
        """根据任务 ID 查找通知记录。"""
        stmt = select(NotificationHistory).where(
            NotificationHistory.mission_id == mission_id
        )
        result = await session.exec(stmt)
        return result.first()

    async def find_by_mission_type(
        self, session: AsyncSession, mission_type: str, limit: int = 50
    ) -> list[NotificationHistory]:
        """根据任务类型查找通知记录。"""
        stmt = (
            select(NotificationHistory)
            .where(NotificationHistory.mission_type == mission_type)
            .order_by(NotificationHistory.notified_at.desc())
            .limit(limit)
        )
        result = await session.exec(stmt)
        return list(result.all())

    async def delete_older_than(
        self, session: AsyncSession, cutoff_time: str
    ) -> int:
        """删除早于指定时间的通知记录。"""
        stmt = sql_delete(NotificationHistory).where(
            NotificationHistory.notified_at < cutoff_time
        )
        result = await session.exec(stmt)
        await session.commit()
        return result.rowcount

    async def count_by_type(self, session: AsyncSession) -> dict[str, int]:
        """统计各类型的通知数量。"""
        stmt = select(
            NotificationHistory.mission_type,
            func.count(NotificationHistory.id),
        ).group_by(NotificationHistory.mission_type)
        result = await session.exec(stmt)
        return dict(result.all())


# 模块级单例
notification_repo = NotificationRepository()
