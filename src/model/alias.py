"""
Alias Model / 别名模型
包含 Warframe 可交易物品的别名映射
"""
from __future__ import annotations

import re

from tortoise import fields
from tortoise.models import Model


class Alias(Model):
    """Warframe 物品的别名表"""

    id = fields.IntField(pk=True, description="自增主键")
    cn = fields.CharField(max_length=255, index=True, unique=True, description="别名名称")
    en = fields.CharField(max_length=255, index=True, description="原名称/被映射的名称")
    is_custom = fields.BooleanField(
        default=False,
        description="是否用户自定义：True 表示通过管理页/接口手工添加，同步时不清除",
    )

    class Meta:
        table = "alias"

    def is_valid_english(self) -> bool:
        """校验英文名称格式"""
        return bool(re.match(r"^([a-zA-Z]+)([ _&])?([0-9]+)?([a-zA-Z]+)?$", self.en))

    def is_valid_chinese(self) -> bool:
        """校验中文名称格式"""
        return bool(re.match(r"^[\u4e00-\u9fa5]+([ ·_&])?[\u4e00-\u9fa5]+$", self.cn))
