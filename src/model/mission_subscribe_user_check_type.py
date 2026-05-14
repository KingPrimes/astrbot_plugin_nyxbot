"""
MissionSubscribeUserCheckType Model / 用户订阅检查类型模型

对应 Java: MissionSubscribeUserCheckType.java
"""
from __future__ import annotations

from typing import Optional
from tortoise import fields
from tortoise.models import Model

from ..wenum.subscribe import SubscribeEnums
from ..wenum.mission_type import MissionTypeEnum


class MissionSubscribeUserCheckType(Model):
    """用户订阅检查类型"""

    id = fields.IntField(pk=True, description="自增主键")

    mission_subscribe_user: fields.ForeignKeyNullableRelation = fields.ForeignKeyField(
        "models.MissionSubscribeUser", related_name="check_types", null=True, on_delete=fields.CASCADE
    )
    subscribe = fields.CharField(max_length=50, description="订阅类型")
    mission_type_enum = fields.CharField(max_length=50, null=True, description="任务类型")
    tier_num = fields.IntField(null=True, description="遗物纪元")
    subscribe_type = fields.CharField(max_length=50, null=True, description="订阅类型（临时）")

    class Meta:
        table = "missionsubscribeuserchecktype"

    @property
    def subscribe_enum(self) -> SubscribeEnums:
        """获取订阅类型枚举"""
        return SubscribeEnums.from_en_name(self.subscribe)

    @property
    def mission_type_enum_value(self) -> Optional[MissionTypeEnum]:
        """获取任务类型枚举"""
        if self.mission_type_enum:
            try:
                return MissionTypeEnum[self.mission_type_enum]
            except (KeyError, ValueError):
                try:
                    return MissionTypeEnum(self.mission_type_enum)
                except ValueError:
                    return None
        return None

    def matches(
        self,
        sub_type: SubscribeEnums,
        mission_type: Optional[MissionTypeEnum] = None,
        tier: Optional[int] = None,
    ) -> bool:
        """检查是否匹配给定的条件"""
        return (
            self.subscribe == sub_type.en_name
            and (mission_type is None or self.mission_type_enum == mission_type.name)
            and (tier is None or self.tier_num == tier)
        )
