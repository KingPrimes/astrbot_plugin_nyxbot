"""Subscription service / 订阅服务

管理群组/用户的 Warframe 任务订阅。

适配的模型字段：
  - MissionSubscribe.sub_bot_uid → Bot UID
  - MissionSubscribe.sub_group   → 群组 ID (unique)
  - MissionSubscribe.group_name  → 群组名称
  - MissionSubscribeUser.user_id → 用户 ID
"""
from __future__ import annotations

from typing import Optional, Sequence

from ..model.mission_subscription import MissionSubscribe, MissionSubscribeUser
from ..model.mission_subscribe_user_check_type import MissionSubscribeUserCheckType


class SubscriptionService:
    """订阅管理服务。"""

    # ── MissionSubscribe ──────────────────────────────────────────────

    @classmethod
    async def add_subscription(
        cls,
        sub_bot_uid: int,
        sub_group: int,
        group_name: Optional[str] = None,
    ) -> MissionSubscribe:
        """添加群组订阅。

        Args:
            sub_bot_uid: 发送消息的 Bot UID。
            sub_group: 订阅群组 ID。
            group_name: 可选的群组名称。

        Returns:
            创建的订阅记录。
        """
        ...

    @classmethod
    async def remove_subscription(cls, sub_group: int) -> bool:
        """删除群组订阅。

        Args:
            sub_group: 订阅群组 ID。

        Returns:
            是否成功删除。
        """
        ...

    # ── MissionSubscribeUser ──────────────────────────────────────────

    @classmethod
    async def add_user_to_subscription(
        cls,
        sub_id: int,
        user_id: int,
        user_name: Optional[str] = None,
    ) -> MissionSubscribeUser:
        """为指定订阅添加用户。

        Args:
            sub_id: 订阅 ID。
            user_id: 用户 ID。
            user_name: 可选的用户名称。

        Returns:
            创建的用户订阅配置。
        """
        ...

    @classmethod
    async def remove_user_from_subscription(
        cls, sub_id: int, user_id: int
    ) -> bool:
        """从指定订阅中移除用户。

        Args:
            sub_id: 订阅 ID。
            user_id: 用户 ID。

        Returns:
            是否成功移除。
        """
        ...

    @classmethod
    async def list_users_by_subscription(
        cls, sub_id: int
    ) -> Sequence[MissionSubscribeUser]:
        """列出指定订阅下的所有用户。

        Args:
            sub_id: 订阅 ID。

        Returns:
            用户订阅配置列表。
        """
        ...

    # ── MissionSubscribeUserCheckType ─────────────────────────────────

    @classmethod
    async def add_check_type(
        cls,
        subscribe_user_id: int,
        subscribe_type: str,
        mission_type: Optional[str] = None,
        tier_num: Optional[int] = None,
    ) -> MissionSubscribeUserCheckType:
        """为用户订阅添加检查类型。

        Args:
            subscribe_user_id: 用户订阅配置 ID。
            subscribe_type: 订阅类型。
            mission_type: 可选的任务类型。
            tier_num: 可选的遗物纪元。

        Returns:
            创建的检查类型记录。
        """
        ...

    @classmethod
    async def remove_check_type(cls, check_type_id: int) -> bool:
        """删除检查类型。

        Args:
            check_type_id: 检查类型 ID。

        Returns:
            是否成功删除。
        """
        ...

    @classmethod
    async def list_check_types(
        cls, subscribe_user_id: int
    ) -> list[MissionSubscribeUserCheckType]:
        """列出用户订阅的检查类型。

        Args:
            subscribe_user_id: 用户订阅配置 ID。

        Returns:
            检查类型列表。
        """
        ...

    # ── 查询 ──────────────────────────────────────────────────────────

    @classmethod
    async def get_subscription_by_group(
        cls, sub_group: int
    ) -> Optional[MissionSubscribe]:
        """根据群组 ID 获取订阅。

        Args:
            sub_group: 群组 ID。

        Returns:
            订阅记录，不存在返回 None。
        """
        ...

    @classmethod
    async def list_all_subscriptions(cls) -> Sequence[MissionSubscribe]:
        """列出所有订阅（含关联的用户和检查类型）。

        Returns:
            所有订阅记录。
        """
        ...

    @classmethod
    async def list_subscriptions_by_bot(
        cls, sub_bot_uid: int
    ) -> list[MissionSubscribe]:
        """列出指定 Bot 的所有订阅。

        Args:
            sub_bot_uid: Bot UID。

        Returns:
            订阅列表。
        """
        ...
