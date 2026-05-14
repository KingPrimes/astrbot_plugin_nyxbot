"""
RivenAnalyseTrend Model / 紫卡分析参数模型

对应 Java: RivenAnalyseTrend.java
"""
from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class RivenAnalyseTrend(Model):
    """紫卡分析参数"""

    id = fields.IntField(pk=True, description="自增主键")
    archwing = fields.FloatField(null=True, description="Archwing枪械")
    melle = fields.FloatField(null=True, description="近战")
    name = fields.CharField(max_length=255, null=True, description="效果名称")
    pistol = fields.FloatField(null=True, description="手枪")
    prefix = fields.CharField(max_length=255, null=True, description="前缀")
    rifle = fields.FloatField(null=True, description="步枪")
    shotgun = fields.FloatField(null=True, description="霰弹枪")
    suffix = fields.CharField(max_length=255, null=True, description="后缀")

    class Meta:
        table = "rivenanalysetrend"

    @property
    def equation(self) -> str:
        """序列化全部字段"""
        return f"{self.archwing}{self.melle}{self.name}{self.pistol}{self.prefix}{self.rifle}{self.shotgun}{self.suffix}"
