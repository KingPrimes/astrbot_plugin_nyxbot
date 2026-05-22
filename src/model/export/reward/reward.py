"""
Reward Model / 具体奖励模型

对应 Java: Reward.java

设计说明：
- 使用 SHA-256(item∥rarity∥itemCount)[:16] 作为确定性主键，同一三元组在任何上下文中都映射到同一个 ID
- Reward 行全局唯一且不可变（字段变化 → 哈希不同 → 新行）
- 跨 Pool 共享通过 M2M 中间表管理，Reward 表不再有 FK 列
"""
from __future__ import annotations

import hashlib

from tortoise import fields
from tortoise.models import Model

from ....wenum.rarity import RarityEnum


class Reward(Model):
    """具体奖励 — 以 (item, rarity, itemCount) 的 SHA-256 哈希为确定性主键，
    同一三元组在任何上下文中都映射到同一个 ID。"""

    id = fields.CharField(max_length=16, pk=True, description="SHA-256[:16] 确定性主键")
    item = fields.CharField(max_length=255, default="", description="奖励物品名称")
    rarity = fields.CharField(max_length=50, null=True, description="稀有度")
    itemCount = fields.IntField(null=True, description="物品数量")

    class Meta:
        table = "reward"

    @staticmethod
    def make_id(item: str, rarity: str | None, item_count: int | None) -> str:
        """根据三元组生成确定性主键（SHA-256 前 16 字符 hex）。

        相同 (item, rarity, itemCount) 永远生成相同 ID，
        实现跨 Pool 的全局 Reward 去重。
        """
        raw = f"{item}\x00{rarity or ''}\x00{item_count or 1}"
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

    def get_item(self) -> str:
        """获取物品名称，替换 |COUNT| 占位符"""
        if self.itemCount and self.itemCount > 1:
            return self.item.replace("|COUNT|", str(self.itemCount))
        return self.item
