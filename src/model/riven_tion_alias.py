"""
RivenTionAlias Model / 紫卡词条别名模型

对应 Java: RivenTionAlias.java
"""
from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class RivenTionAlias(Model):
    """紫卡词条别名"""

    id = fields.IntField(pk=True, description="唯一自增ID")
    en = fields.CharField(max_length=255, null=True, description="英文")
    cn = fields.CharField(max_length=255, null=True, description="中文")

    class Meta:
        table = "riventionalias"

    @property
    def equation(self) -> str:
        """序列化全部字段"""
        return f"{self.en}{self.cn}"
