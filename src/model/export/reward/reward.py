"""
Reward Model / 具体奖励模型

对应 Java: Reward.java
"""
from __future__ import annotations

from typing import Optional
from tortoise import fields
from tortoise.models import Model

from ....wenum.rarity import RarityEnum


class Reward(Model):
    """具体奖励"""

    id = fields.CharField(max_length=255, pk=True, description="UUID 主键")
    item = fields.CharField(max_length=255, default="", description="奖励物品名称")
    rarity = fields.CharField(max_length=50, null=True, description="稀有度")
    itemCount = fields.IntField(null=True, source_field="unique_name", description="物品数量")

    reward_pool: fields.ForeignKeyNullableRelation = fields.ForeignKeyField(
        "models.RewardPool", related_name="rewards", null=True, on_delete=fields.CASCADE
    )

    class Meta:
        table = "reward"

    @property
    def rarity_enum(self) -> Optional[RarityEnum]:
        """获取稀有度枚举"""
        if self.rarity:
            try:
                return RarityEnum[self.rarity]
            except (KeyError, ValueError):
                return RarityEnum.from_en_name(self.rarity)
        return None

    def get_item(self) -> str:
        """获取物品名称，替换 |COUNT| 占位符"""
        if self.itemCount and self.itemCount > 1:
            return self.item.replace("|COUNT|", str(self.itemCount))
        return self.item
