"""
ModSet Model / MOD套装模型

对应 Java: ModSet.java
"""
from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class ModSet(Model):
    """MOD 套装"""

    uniqueName = fields.CharField(max_length=255, pk=True, source_field="unique_name", description="唯一名称")
    numUpgradesInSet = fields.IntField(null=True, source_field="num_upgrades_in_set", description="套装内MOD数量")
    buffSet = fields.BooleanField(null=True, source_field="buff_set", description="是否为增益套装")
    stats = fields.TextField(null=True, description="属性描述")

    class Meta:
        table = "modset"
