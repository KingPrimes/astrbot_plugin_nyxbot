"""Subscription Model / 订阅模型

对应 Java: MissionSubscribe.java, MissionSubscribeUser.java
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from tortoise import fields
from tortoise.models import Model

if TYPE_CHECKING:
    from .mission_subscribe_user_check_type import MissionSubscribeUserCheckType


class MissionSubscribe(Model):
    """任务订阅配置"""

    id = fields.IntField(pk=True, description="自增主键")
    group_name = fields.CharField(max_length=255, null=True, description="群组名称")
    sub_bot_uid = fields.IntField(description="发送消息的Bot UID")
    sub_group = fields.IntField(unique=True, description="订阅群组")

    users: fields.ReverseRelation["MissionSubscribeUser"]

    class Meta:
        table = "missionsubscribe"


class MissionSubscribeUser(Model):
    """用户订阅配置"""

    id = fields.IntField(pk=True, description="自增主键")
    user_id = fields.IntField(description="用户 ID")
    user_name = fields.CharField(max_length=255, null=True, description="用户名称")

    mission_subscribe: fields.ForeignKeyNullableRelation[MissionSubscribe] = fields.ForeignKeyField(
        "models.MissionSubscribe", related_name="users", null=True, on_delete=fields.CASCADE
    )
    check_types: fields.ReverseRelation["MissionSubscribeUserCheckType"]

    class Meta:
        table = "missionsubscribeuser"
