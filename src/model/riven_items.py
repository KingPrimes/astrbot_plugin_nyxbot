"""
RivenItems Model / 紫卡数据模型

对应 Java: RivenItems.java
"""
from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class RivenItems(Model):
    """Warframe Riven 数据"""

    id = fields.CharField(max_length=255, pk=True, description="紫卡ID")
    slug = fields.CharField(max_length=255, null=True, description="URL名称")
    gameRef = fields.CharField(max_length=255, null=True, source_field="game_ref", description="Lotus引用")
    group = fields.CharField(max_length=255, null=True, description="分组")
    rivenType = fields.CharField(max_length=255, null=True, source_field="riven_type", description="紫卡类型")
    disposition = fields.FloatField(null=True, description="倾向数值")
    reqMasteryRank = fields.IntField(null=True, source_field="req_mastery_rank", description="等级限制")
    name = fields.CharField(max_length=255, null=True, description="物品名称")
    icon = fields.CharField(max_length=500, null=True, description="图标")
    thumb = fields.CharField(max_length=500, null=True, description="缩略图")

    class Meta:
        table = "rivenitems"
