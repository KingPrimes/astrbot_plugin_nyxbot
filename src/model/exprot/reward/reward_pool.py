"""
RewardPool Model / 奖励池模型

对应 Java: RewardPool.java
"""
from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class RewardPool(Model):
    """奖励池"""

    uniqueName = fields.CharField(max_length=255, pk=True, source_field="unique_name", description="唯一名称")
    rewards: fields.ReverseRelation

    class Meta:
        table = "rewardpool"
