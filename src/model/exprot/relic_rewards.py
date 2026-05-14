"""
RelicRewards Model / 遗物奖励模型

对应 Java: RelicRewards.java
"""
from __future__ import annotations

from typing import Optional
from tortoise import fields
from tortoise.models import Model

from ...wenum.rarity import RarityEnum


class RelicRewards(Model):
    """遗物奖励"""

    id = fields.CharField(max_length=255, pk=True, description="UUID 主键")
    rewardName = fields.CharField(max_length=255, null=True, source_field="reward_name", description="奖励名称")
    rarity = fields.CharField(max_length=50, null=True, description="稀有度")
    tier = fields.IntField(null=True, description="等级")
    itemCount = fields.IntField(null=True, source_field="item_count", description="物品数量")

    relics: fields.ForeignKeyNullableRelation = fields.ForeignKeyField(
        "models.Relics", related_name="relic_rewards", null=True, on_delete=fields.CASCADE
    )

    class Meta:
        table = "relicrewards"

    @property
    def rarity_enum(self) -> Optional[RarityEnum]:
        """获取稀有度枚举"""
        if self.rarity:
            try:
                return RarityEnum[self.rarity]
            except (KeyError, ValueError):
                return RarityEnum.from_en_name(self.rarity)
        return None

    def get_reward_name(self) -> str:
        """获取奖励名称，如果数量大于1则添加数量前缀"""
        if self.itemCount and self.itemCount > 1:
            return f"{self.itemCount}X{self.rewardName}"
        return self.rewardName or ""
