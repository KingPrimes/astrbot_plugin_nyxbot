"""
Upgrades Model / MOD及升级组件模型

对应 Java: Upgrades.java
"""
from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class Upgrades(Model):
    """MOD / 升级组件"""

    uniqueName = fields.CharField(max_length=255, pk=True, source_field="unique_name", description="唯一名称")
    name = fields.CharField(max_length=255, null=True, description="名称")
    polarity = fields.CharField(max_length=100, null=True, description="极性")
    rarity = fields.CharField(max_length=100, null=True, description="稀有度")
    codexSecret = fields.BooleanField(null=True, source_field="codex_secret", description="是否保密")
    baseDrain = fields.IntField(null=True, source_field="base_drain",description="基础容量消耗")
    fusionLimit = fields.IntField(null=True, source_field="fusion_limit", description="融合上限")
    compatName = fields.CharField(max_length=255, null=True, source_field="compat_name", description="兼容名称")
    type = fields.CharField(max_length=100, null=True, description="类型")
    tag = fields.CharField(max_length=100, null=True, description="标签")
    stats = fields.TextField(null=True, description="属性")
    modSet = fields.CharField(max_length=255, null=True, source_field="mod_set", description="MOD套装")

    class Meta:
        table = "upgrades"
