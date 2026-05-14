"""
RivenTion Model / 紫卡词条参数模型

对应 Java: RivenTion.java
"""
from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class RivenTion(Model):
    """紫卡词条参数"""

    ids = fields.IntField(pk=True, description="唯一自增ID")
    effect = fields.CharField(max_length=255, null=True, description="词条名称")
    group = fields.CharField(max_length=255, null=True, description="分组")
    negative_only = fields.FloatField(null=True, description="仅负属性")
    positive_is_negative = fields.FloatField(null=True, description="")
    prefix = fields.CharField(max_length=255, null=True, description="前缀")
    search_only = fields.FloatField(null=True, description="仅搜索")
    suffix = fields.CharField(max_length=255, null=True, description="后缀")
    units = fields.CharField(max_length=255, null=True, description="单位")
    url_name = fields.CharField(max_length=255, null=True, description="URL名称")
    exclusive_to = fields.CharField(max_length=255, null=True, description="可用武器类型")

    class Meta:
        table = "rivention"

    @property
    def equation(self) -> str:
        """序列化全部字段"""
        return (
            f"{self.effect}{self.group}{self.negative_only}{self.positive_is_negative}"
            f"{self.prefix}{self.search_only}{self.suffix}{self.units}{self.url_name}{self.exclusive_to}"
        )
