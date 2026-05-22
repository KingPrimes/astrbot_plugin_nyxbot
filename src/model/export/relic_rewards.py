"""
RelicRewards Model / 遗物奖励模型

对应 Java: RelicRewards.java

设计说明：
- 使用 SHA-256(rewardName∥rarity∥tier∥itemCount)[:16] 作为确定性主键，
  同一四元组在任何上下文中都映射到同一个 ID
- RelicRewards 行全局唯一且不可变（字段变化 → 哈希不同 → 新行）
- 跨 Relics 共享通过 M2M 中间表管理，RelicRewards 表不再有 FK 列
"""
from __future__ import annotations

import hashlib

from tortoise import fields
from tortoise.models import Model

from ...wenum.rarity import RarityEnum


class RelicRewards(Model):
    """遗物奖励 — 确定性哈希主键，跨遗物共享"""

    id = fields.CharField(max_length=16, pk=True, description="SHA-256[:16] 确定性主键")
    rewardName = fields.CharField(max_length=255, null=True, description="奖励名称")
    rarity = fields.CharField(max_length=50, null=True, description="稀有度")
    tier = fields.IntField(null=True, description="等级")
    itemCount = fields.IntField(null=True, description="物品数量")

    class Meta:
        table = "relicrewards"

    @staticmethod
    def make_id(reward_name: str, rarity: str | None, tier: int | None, item_count: int | None) -> str:
        """根据四元组生成确定性主键（SHA-256 前 16 字符 hex）。

        相同 (rewardName, rarity, tier, itemCount) 永远生成相同 ID，
        实现跨 Relics 的全局 RelicRewards 去重。
        """
        raw = f"{reward_name or ''}\x00{rarity or ''}\x00{tier or 0}\x00{item_count or 1}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    @property
    def rarity_enum(self) -> RarityEnum | None:
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
