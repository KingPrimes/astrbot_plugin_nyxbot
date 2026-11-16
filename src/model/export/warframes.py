"""
Warframes Model / 战甲模型

对应 Java: Warframes.java
"""
from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class WarframeAbility(Model):
    """战甲技能。

    主键用自增 ``id`` 而不是 ``abilityUniqueName``：导出文件里同一技能会挂在
    多个战甲上（508 条技能只有 295 个唯一名称，例如 Archwing 的
    ``FireShieldAbility``、阴阳甲的 4 个技能），拿技能名当主键会把后一个战甲
    的记录覆盖掉。
    """

    id = fields.IntField(pk=True)
    abilityUniqueName = fields.CharField(max_length=255, description="技能唯一名称")
    abilityName = fields.CharField(max_length=255, null=True, description="技能名称")
    description = fields.TextField(null=True, description="技能描述")

    warframe: fields.ForeignKeyNullableRelation = fields.ForeignKeyField(
        "models.Warframes", related_name="abilities", null=True, on_delete=fields.CASCADE
    )

    class Meta:
        table = "warframeability"


class Warframes(Model):
    """战甲"""

    uniqueName = fields.CharField(max_length=255, pk=True, description="唯一名称")
    name = fields.CharField(max_length=255, null=True, description="名称")
    parentName = fields.CharField(max_length=255, null=True, description="上级名称")
    description = fields.TextField(null=True, description="描述")
    health = fields.IntField(null=True, description="生命值")
    shield = fields.IntField(null=True, description="护盾")
    armor = fields.IntField(null=True, description="护甲")
    stamina = fields.IntField(null=True, description="耐力")
    power = fields.IntField(null=True, description="能量")
    codexSecret = fields.BooleanField(null=True, description="是否保密")
    masteryReq = fields.IntField(null=True, description="段位需求")
    sprintSpeed = fields.FloatField(null=True, description="冲刺速度")
    productCategory = fields.CharField(max_length=100, null=True, description="类别")

    # ── 说明文本与显赫武器：ExportWarframes 直接提供 ──

    passiveDescription = fields.TextField(null=True, description="被动描述")
    longDescription = fields.TextField(null=True, description="长描述")
    exalted = fields.TextField(null=True, description="显赫武器 uniqueName 列表（JSON序列化）")
    excludeFromCodex = fields.BooleanField(null=True, description="是否从资料库排除")

    abilities: fields.ReverseRelation[WarframeAbility]

    class Meta:
        table = "warframes"
