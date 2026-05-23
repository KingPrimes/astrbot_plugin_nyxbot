"""
Reward Model / 任务奖励模型
独立奖励模型，被 Alert.MissionInfo 和 Invasion 等多处引用。

对应 Java: Reward.java
"""
from __future__ import annotations

from pydantic import Field

from .base import BaseModelWithAlias


class Reward(BaseModelWithAlias):
    """任务奖励 / Mission Reward

    对应 Java: Reward.java
    """

    class Item(BaseModelWithAlias):
        """有数量的奖励物品 / Counted reward item

        JSON 格式: {"ItemType": "/Lotus/...", "ItemCount": 3}

        对应 Java: Reward.Item
        """
        name: str = Field(alias="ItemType")
        count: int = Field(alias="ItemCount")
    credits: int | None = Field(default=None, alias="credits")
    xp: int | None = Field(default=None, alias="xp")
    items: list[str] = Field(default_factory=list, alias="items")
    counted_items: list[Item] = Field(default_factory=list, alias="countedItems")

