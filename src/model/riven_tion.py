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
    negative_only = fields.BooleanField(null=True, description="仅负属性（API: negativeOnly）")
    positive_is_negative = fields.BooleanField(null=True, description="正值视为负（API: positiveIsNegative）")
    prefix = fields.CharField(max_length=255, null=True, description="前缀")
    search_only = fields.BooleanField(null=True, description="仅搜索（API 文档无对应字段）")
    suffix = fields.CharField(max_length=255, null=True, description="后缀")
    unit = fields.CharField(max_length=255, null=True, description="计量单位（API: unit）")
    url_name = fields.CharField(max_length=255, null=True, description="URL名称")
    exclusive_to = fields.CharField(max_length=255, null=True, description="可用武器类型")

    class Meta:
        table = "rivention"

    @property
    def equation(self) -> str:
        """序列化全部字段"""
        return (
            f"{self.effect}{self.group}{self.negative_only}{self.positive_is_negative}"
            f"{self.prefix}{self.search_only}{self.suffix}{self.unit}{self.url_name}{self.exclusive_to}"
        )
