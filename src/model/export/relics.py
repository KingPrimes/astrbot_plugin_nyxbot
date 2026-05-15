"""
Relics Model / 遗物模型

对应 Java: Relics.java
"""
from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class Relics(Model):
    """遗物"""

    uniqueName = fields.CharField(max_length=255, pk=True, source_field="unique_name", description="唯一名称")
    name = fields.CharField(max_length=255, null=True, description="名称")
    codexSecret = fields.BooleanField(null=True, source_field="codex_secret", description="是否保密")
    description = fields.TextField(null=True, description="描述")

    relic_rewards: fields.ReverseRelation

    class Meta:
        table = "relics"
