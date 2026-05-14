"""Notification Model / 通知历史模型

对应 Java: NotificationHistory.java
"""
from __future__ import annotations

from typing import Optional
from tortoise import fields
from tortoise.models import Model

from ..wenum.subscribe import SubscribeEnums


class NotificationHistory(Model):
    """通知历史记录
    用于防止重复通知
    """

    id = fields.IntField(pk=True, description="自增主键")
    subscribe_type = fields.CharField(max_length=50, null=True, description="订阅类型")
    mission_type = fields.CharField(max_length=255, description="任务类型")
    mission_id = fields.CharField(max_length=255, description="任务唯一 ID")
    title = fields.CharField(max_length=255, default="", description="通知标题")
    content = fields.TextField(default="", description="通知内容")
    expiry_timestamp = fields.IntField(default=0, description="周期过期时间戳（秒）")
    notified_at = fields.CharField(max_length=50, description="通知时间")
    notified_users = fields.TextField(default="", description="已通知的用户 ID 列表（逗号分隔）")
    cycle_state = fields.CharField(max_length=255, null=True, description="周期状态")

    class Meta:
        table = "notificationhistory"

    @property
    def subscribe_type_enum(self) -> Optional[SubscribeEnums]:
        """获取订阅类型枚举"""
        if self.subscribe_type:
            try:
                return SubscribeEnums(self.subscribe_type)
            except ValueError:
                return SubscribeEnums.from_en_name(self.subscribe_type)
        return None
