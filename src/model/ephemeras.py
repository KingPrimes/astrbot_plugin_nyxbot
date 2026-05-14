"""
Ephemeras Model / 幻纹模型

对应 Java: Ephemeras.java
"""
from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class Ephemeras(Model):
    """Warframe 幻纹"""

    id = fields.CharField(max_length=255, pk=True, description="唯一ID")
    slug = fields.CharField(max_length=50, null=True, description="URL路径名称")
    gameRef = fields.CharField(max_length=255, null=True, source_field="game_ref", description="Lotus引用")
    animation = fields.CharField(max_length=120, null=True, description="动画")
    element = fields.CharField(max_length=20, null=True, description="元素")
    name = fields.CharField(max_length=80, null=True, description="名称")
    icon = fields.CharField(max_length=120, null=True, description="图标")
    thumb = fields.CharField(max_length=120, null=True, description="缩略图")

    class Meta:
        table = "ephemeras"
