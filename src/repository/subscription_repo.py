"""Subscription repository / 订阅数据访问层"""
from __future__ import annotations

from typing import Optional, Sequence

from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from ..model.subscription import MissionSubscribe
from .base import BaseRepository


class SubscriptionRepository(BaseRepository[MissionSubscribe]):
    """订阅数据访问对象。"""

    def __init__(self):
        super().__init__(MissionSubscribe)

    async def find_by_user(
        self, session: AsyncSession, user_id: str
    ) -> Sequence[MissionSubscribe]:
        """查找用户的所有订阅。"""
        stmt = select(MissionSubscribe).where(
            MissionSubscribe.user_id == user_id
        )
        result = await session.exec(stmt)
        return result.all()

    async def find_by_group(
        self, session: AsyncSession, group_id: str
    ) -> Sequence[MissionSubscribe]:
        """查找群组的所有订阅。"""
        stmt = select(MissionSubscribe).where(
            MissionSubscribe.group_id == group_id
        )
        result = await session.exec(stmt)
        return result.all()

    async def find_by_type(
        self, session: AsyncSession, mission_type: str
    ) -> Sequence[MissionSubscribe]:
        """查找指定任务类型的所有订阅。"""
        stmt = select(MissionSubscribe).where(
            MissionSubscribe.mission_type == mission_type,
            MissionSubscribe.enabled == True,
        )
        result = await session.exec(stmt)
        return result.all()

    async def find_existing(
        self,
        session: AsyncSession,
        user_id: str,
        group_id: str,
        mission_type: str,
    ) -> Optional[MissionSubscribe]:
        """查找已存在的订阅。"""
        stmt = select(MissionSubscribe).where(
            MissionSubscribe.user_id == user_id,
            MissionSubscribe.group_id == group_id,
            MissionSubscribe.mission_type == mission_type,
        )
        result = await session.exec(stmt)
        return result.first()

    async def toggle(
        self, session: AsyncSession, sub_id: int
    ) -> Optional[MissionSubscribe]:
        """切换订阅启用/禁用状态。"""
        sub = await self.get_by_id(session, sub_id)
        if sub is None:
            return None
        sub.enabled = not sub.enabled
        return await self.update(session, sub)


# 模块级单例
subscription_repo = SubscriptionRepository()
