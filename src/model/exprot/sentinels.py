"""
Sentinels Model / 守护/宠物模型

对应 Java: Sentinels.java
"""
from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class Sentinels(Model):
    """守护/宠物"""

    uniqueName = fields.CharField(max_length=255, pk=True, source_field="unique_name", description="唯一名称")
    name = fields.CharField(max_length=255, null=True, description="名称")
    health = fields.IntField(null=True, description="生命值")
    shield = fields.IntField(null=True, description="护盾")
    armor = fields.IntField(null=True, description="护甲")
    stamina = fields.IntField(null=True, description="耐力")
    power = fields.IntField(null=True, description="能量")
    codexSecret = fields.BooleanField(null=True, source_field="codex_secret", description="是否保密")
    excludeFromCodex = fields.BooleanField(null=True, source_field="exclude_from_codex", description="是否排除")
    description = fields.TextField(null=True, description="描述")
    productCategory = fields.CharField(max_length=100, null=True, source_field="product_category", description="类别")

    class Meta:
        table = "sentinels"
