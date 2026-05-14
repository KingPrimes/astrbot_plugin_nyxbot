"""
LichSisterWeapons Model / 信条/赤毒武器模型

对应 Java: LichSisterWeapons.java
"""
from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class LichSisterWeapons(Model):
    """信条/赤毒武器"""

    id = fields.CharField(max_length=255, pk=True, description="唯一字符串武器ID")
    slug = fields.CharField(max_length=255, null=True, description="URL路径名称")
    icon = fields.CharField(max_length=500, null=True, description="武器图标")
    gameRef = fields.CharField(max_length=255, null=True, source_field="game_ref", description="Lotus名称")
    reqMasteryRank = fields.IntField(null=True, source_field="req_mastery_rank", description="段位限制")
    name = fields.CharField(max_length=255, null=True, description="武器名称")
    thumb = fields.CharField(max_length=500, null=True, description="缩略图")

    class Meta:
        table = "lichsisterweapons"
