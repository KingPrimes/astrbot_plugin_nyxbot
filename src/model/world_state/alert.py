"""
Alert Model / 警报任务模型

对应 Java: Alert.java
继承 BastWorldState，包含 ForceUnlock、Tag、MissionInfo（嵌套类）。
"""
from __future__ import annotations

from pydantic import Field

from ...wenum.faction import FactionEnum
from ...wenum.mission_type import MissionTypeEnum
from .base import BaseModelWithAlias, BastWorldState


class Alert(BastWorldState):
    """警报任务 / Alert Mission

    对应 Java: Alert extends BastWorldState
    """

    class MissionInfoReward(BastWorldState):
        """警报任务奖励（嵌套在 MissionInfo 中）/ Alert Mission Reward

        Java: Alert.MissionInfo.Reward

        JSON 格式: {"credits": 17000, "countedItems": [{"ItemType": "...", "ItemCount": 10}]}
        """

        class Item(BaseModelWithAlias):
            """有数量的奖励物品 / Counted reward item

            JSON 格式: {"ItemType": "/Lotus/...", "ItemCount": 3}
            """
            name: str = Field(alias="ItemType")
            count: int = Field(alias="ItemCount")
        credits: int | None = Field(default=None, alias="credits")
        counted_items: list[Item] = Field(default_factory=list, alias="countedItems")
    class MissionInfo(BastWorldState):
        """警报任务详情 / Alert Mission Info

        Java: Alert.MissionInfo
        """
        desc_text: str | None = Field(default=None, alias="descText")
        difficulty: int | None = Field(default=None, alias="difficulty")
        enemy_spec: str | None = Field(default=None, alias="enemySpec")
        faction: FactionEnum | None = Field(default=None, alias="faction")
        level_override: str | None = Field(default=None, alias="levelOverride")
        location: str | None = Field(default=None, alias="location")
        max_enemy_level: int | None = Field(default=None, alias="maxEnemyLevel")
        max_wave_num: int | None = Field(default=None, alias="maxWaveNum")
        min_enemy_level: int | None = Field(default=None, alias="minEnemyLevel")
        mission_type: MissionTypeEnum | None = Field(default=None, alias="missionType")
        seed: int | None = Field(default=None, alias="seed")
        mission_reward: Alert.MissionInfoReward | None = Field(default=None, alias="missionReward")
        quest_req: str | None = Field(default=None, alias="questReq")
        leaders_always_allowed: bool | None = Field(default=None, alias="leadersAlwaysAllowed")
    force_unlock: bool | None = Field(default=None, alias="ForceUnlock")
    tag: str | None = Field(default=None, alias="Tag")
    mission_info: MissionInfo | None = Field(default=None, alias="MissionInfo")

