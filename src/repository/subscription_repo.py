"""Subscription repository / 订阅数据访问层

适配 MissionSubscribe / MissionSubscribeUser / MissionSubscribeUserCheckType 模型。
"""
from __future__ import annotations

from typing import Optional, Sequence

from tortoise.exceptions import DoesNotExist

from ..model.mission_subscription import MissionSubscribe, MissionSubscribeUser
from ..model.mission_subscribe_user_check_type import MissionSubscribeUserCheckType
from .base import BaseRepository


class SubscriptionRepository(BaseRepository[MissionSubscribe]):
    """任务订阅数据访问对象。"""

    def __init__(self):
        super().__init__(MissionSubscribe)

    # ── MissionSubscribe ──────────────────────────────────────────────

    async def find_by_sub_group(
        self, sub_group: int
    ) -> Optional[MissionSubscribe]:
        """根据 sub_group 查找订阅群组。"""
        try:
            return await MissionSubscribe.get(sub_group=sub_group)
        except DoesNotExist:
            return None

    async def find_by_sub_bot_uid(
        self, sub_bot_uid: int
    ) -> list[MissionSubscribe]:
        """根据 Bot UID 查找所有相关订阅。"""
        return await MissionSubscribe.filter(sub_bot_uid=sub_bot_uid).prefetch_related("users__check_types")

    async def list_all_active(self) -> Sequence[MissionSubscribe]:
        """列出所有订阅（含关联的 users / check_types）。"""
        return await MissionSubscribe.all().prefetch_related("users__check_types")

    # ── MissionSubscribeUser ──────────────────────────────────────────

    async def find_user_by_id(
        self, user_id: int
    ) -> list[MissionSubscribeUser]:
        """根据 user_id 查找用户的订阅配置。"""
        return await MissionSubscribeUser.filter(user_id=user_id).prefetch_related("check_types")

    async def add_user(
        self, user: MissionSubscribeUser
    ) -> MissionSubscribeUser:
        """添加用户订阅配置。"""
        await user.save()
        return user

    async def remove_user(self, user_id: int) -> bool:
        """删除用户订阅配置。"""
        deleted = await MissionSubscribeUser.filter(user_id=user_id).delete()
        return deleted > 0

    # ── MissionSubscribeUserCheckType ─────────────────────────────────

    async def find_check_types_by_user(
        self, subscribe_user_id: int
    ) -> list[MissionSubscribeUserCheckType]:
        """查找指定用户订阅的所有检查类型。"""
        return await MissionSubscribeUserCheckType.filter(
            mission_subscribe_user_id=subscribe_user_id
        )

    async def add_check_type(
        self, check_type: MissionSubscribeUserCheckType
    ) -> MissionSubscribeUserCheckType:
        """添加检查类型。"""
        await check_type.save()
        return check_type

    async def remove_check_type(self, check_type_id: int) -> bool:
        """删除检查类型。"""
        deleted = await MissionSubscribeUserCheckType.filter(id=check_type_id).delete()
        return deleted > 0


# 模块级单例
subscription_repo = SubscriptionRepository()
