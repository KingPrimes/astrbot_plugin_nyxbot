"""
RewardPool Model / 奖励池模型

对应 Java: RewardPool.java

设计说明：
- 通过 ManyToManyField 与 Reward 建立关联，Tortoise ORM 自动创建中间表 rewardpool_reward
"""
from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class RewardPool(Model):
    """奖励池"""

    uniqueName = fields.CharField(max_length=255, pk=True, description="唯一名称")
    rewards = fields.ManyToManyField(
        "models.Reward",
        related_name="pools",
        description="关联的奖励列表（通过中间表 rewardpool_reward 管理）",
    )

    class Meta:
        table = "rewardpool"
