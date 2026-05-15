"""
Warframes Model / 战甲模型

对应 Java: Warframes.java
"""
from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class WarframeAbility(Model):
    """战甲技能"""

    abilityUniqueName = fields.CharField(max_length=255, pk=True, source_field="ability_unique_name", description="技能唯一名称")
    abilityName = fields.CharField(max_length=255, null=True, source_field="ability_name", description="技能名称")
    description = fields.TextField(null=True, description="技能描述")

    warframe: fields.ForeignKeyNullableRelation = fields.ForeignKeyField(
        "models.Warframes", related_name="abilities", null=True, on_delete=fields.CASCADE
    )

    class Meta:
        table = "warframeability"


class Warframes(Model):
    """战甲"""

    uniqueName = fields.CharField(max_length=255, pk=True, source_field="unique_name", description="唯一名称")
    name = fields.CharField(max_length=255, null=True, description="名称")
    parentName = fields.CharField(max_length=255, null=True, source_field="parent_name", description="上级名称")
    description = fields.TextField(null=True, description="描述")
    health = fields.IntField(null=True, description="生命值")
    shield = fields.IntField(null=True, description="护盾")
    armor = fields.IntField(null=True, description="护甲")
    stamina = fields.IntField(null=True, description="耐力")
    power = fields.IntField(null=True, description="能量")
    codexSecret = fields.BooleanField(null=True, source_field="codex_secret", description="是否保密")
    masteryReq = fields.IntField(null=True, source_field="mastery_req", description="段位需求")
    sprintSpeed = fields.IntField(null=True, source_field="sprint_speed", description="冲刺速度")
    productCategory = fields.CharField(max_length=100, null=True, source_field="product_category", description="类别")

    abilities: fields.ReverseRelation["WarframeAbility"]

    class Meta:
        table = "warframes"
