"""Subscription service / 订阅服务

管理用户/群组的任务订阅。
"""
from __future__ import annotations

from typing import Optional, Sequence

from astrbot.api import logger

from ..init import get_session
from ..model.subscription import MissionSubscribe
from ..repository.subscription_repo import subscription_repo


class SubscriptionService:
    """订阅管理服务。"""

    @classmethod
    async def add_subscription(
        cls,
        user_id: str,
        group_id: str,
        mission_type: str,
    ) -> MissionSubscribe:
        """添加订阅。

        Args:
            user_id: 用户 ID。
            group_id: 群组 ID。
            mission_type: 任务类型。

        Returns:
            创建的订阅记录。
        """
        async with get_session() as session:
            # 检查是否已存在
            existing = await subscription_repo.find_existing(
                session, user_id, group_id, mission_type
            )
            if existing:
                if not existing.enabled:
                    existing.enabled = True
                    return await subscription_repo.update(session, existing)
                return existing

            sub = MissionSubscribe(
                user_id=user_id,
                group_id=group_id,
                mission_type=mission_type,
                enabled=True,
            )
            return await subscription_repo.add(session, sub)

    @classmethod
    async def remove_subscription(
        cls,
        user_id: str,
        group_id: str,
        mission_type: str,
    ) -> bool:
        """删除订阅。

        Args:
            user_id: 用户 ID。
            group_id: 群组 ID。
            mission_type: 任务类型。

        Returns:
            是否成功删除。
        """
        async with get_session() as session:
            existing = await subscription_repo.find_existing(
                session, user_id, group_id, mission_type
            )
            if existing is None:
                return False
            return await subscription_repo.delete(session, existing.id)

    @classmethod
    async def toggle_subscription(cls, sub_id: int) -> bool:
        """切换订阅启用状态。

        Args:
            sub_id: 订阅 ID。

        Returns:
            切换后的状态。
        """
        async with get_session() as session:
            sub = await subscription_repo.toggle(session, sub_id)
            return sub.enabled if sub else False

    @classmethod
    async def list_user_subscriptions(
        cls, user_id: str
    ) -> Sequence[MissionSubscribe]:
        """列出用户的所有订阅。"""
        async with get_session() as session:
            return await subscription_repo.find_by_user(session, user_id)

    @classmethod
    async def list_group_subscriptions(
        cls, group_id: str
    ) -> Sequence[MissionSubscribe]:
        """列出群组的所有订阅。"""
        async with get_session() as session:
            return await subscription_repo.find_by_group(session, group_id)

    @classmethod
    async def get_subscribers_by_type(
        cls, mission_type: str
    ) -> Sequence[MissionSubscribe]:
        """获取指定任务类型的所有订阅者。"""
        async with get_session() as session:
            return await subscription_repo.find_by_type(session, mission_type)
