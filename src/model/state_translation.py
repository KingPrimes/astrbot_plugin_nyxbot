"""
StateTranslation Model / 状态翻译模型

对应 Java: StateTranslation.java
"""
from __future__ import annotations

from typing import Optional
from tortoise import fields
from tortoise.models import Model

from ..wenum.state_type import StateTypeEnum


class StateTranslation(Model):
    """Warframe 物品状态/翻译"""

    uniqueName = fields.CharField(max_length=255, pk=True, source_field="unique_name", description="唯一名词")
    name = fields.CharField(max_length=255, description="名称")
    description = fields.TextField(null=True, description="解释")
    type = fields.CharField(max_length=50, null=True, description="类型")
    parentName = fields.CharField(max_length=255, null=True, source_field="parent_name", description="能否交易")

    class Meta:
        table = "statetranslation"

    @property
    def type_enum(self) -> Optional[StateTypeEnum]:
        """获取状态类型枚举"""
        if self.type:
            try:
                return StateTypeEnum[self.type]
            except (KeyError, ValueError):
                return None
        return None

    def get_description(self) -> str:
        """获取描述，如果为 None 则返回空字符串"""
        if self.description is None:
            return ""
        return self.description

    def set_description(self, description: object) -> None:
        """设置描述，支持列表类型处理"""
        if isinstance(description, list):
            if description:
                self.description = str(description[0])
            else:
                self.description = ""
        else:
            self.description = str(description)

    @property
    def equation(self) -> str:
        """序列化标识"""
        name_upper = (self.name or "").upper().strip()
        unique_upper = (self.uniqueName or "").upper().strip()
        import re
        name_trimmed = re.sub(r"[^a-zA-Z0-9]", "", name_upper)
        unique_trimmed = re.sub(r"[^a-zA-Z0-9]", "", unique_upper)
        return name_trimmed + unique_trimmed
