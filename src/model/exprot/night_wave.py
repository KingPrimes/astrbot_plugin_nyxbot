"""
NightWave Model / 电波任务模型

对应 Java: NightWave.java
"""
from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class NightWave(Model):
    """电波任务"""

    uniqueName = fields.CharField(max_length=255, pk=True, source_field="unique_name", description="唯一名称")
    name = fields.CharField(max_length=255, null=True, description="任务名称")
    description = fields.TextField(null=True, description="任务描述")
    standing = fields.IntField(null=True, description="声望数值")
    required = fields.IntField(null=True, description="任务数量")

    class Meta:
        table = "nightwave"

    def get_description(self) -> str:
        """获取描述，替换 |COUNT| 占位符"""
        if not self.description:
            return ""
        return self.description.replace("|COUNT|", str(self.required or ""))

    @property
    def is_daily_tasks(self) -> bool:
        """是否是每日任务"""
        return self.standing == 1000

    @property
    def is_weekly_tasks(self) -> bool:
        """是否是周任务"""
        return self.standing == 4500

    @property
    def is_elite_missions(self) -> bool:
        """是否是精英任务"""
        return self.standing == 7000
