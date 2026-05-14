"""
Customs Model / 外观模型

对应 Java: Customs.java
"""
from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class Customs(Model):
    """外观"""

    uniqueName = fields.CharField(max_length=255, pk=True, source_field="unique_name", description="唯一名称")
    name = fields.CharField(max_length=255, null=True, description="名称")
    codexSecret = fields.BooleanField(null=True, source_field="codex_secret", description="是否是保密")
    excludeFromCodex = fields.BooleanField(null=True, source_field="exclude_from_codex", description="是否排除")
    description = fields.TextField(null=True, description="描述")

    class Meta:
        table = "customs"
