"""
Relics Model / 遗物模型

对应 Java: Relics.java

设计说明：
- 通过 ManyToManyField 与 RelicRewards 建立关联，Tortoise ORM 自动创建中间表 relics_relicrewards
"""
from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class Relics(Model):
    """遗物"""

    uniqueName = fields.CharField(max_length=255, pk=True, description="唯一名称")
    name = fields.CharField(max_length=255, null=True, description="名称")
    codexSecret = fields.BooleanField(null=True, description="是否保密")
    description = fields.TextField(null=True, description="描述")

    relic_rewards = fields.ManyToManyField(
        "models.RelicRewards",
        related_name="relics",
        description="关联的遗物奖励列表（通过中间表 relics_relicrewards 管理）",
    )

    class Meta:
        table = "relics"
