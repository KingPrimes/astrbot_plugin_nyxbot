"""
MissionInfo Model / 入侵任务详情模型

对应 Java: MissionInfo.java（独立文件，非 Alert.MissionInfo）
不继承 BastWorldState，包含 seed、faction（FactionEnum）、missionReward（list[Reward]）。
用于 Invasion 的 AttackerMissionInfo / DefenderMissionInfo。
"""
from __future__ import annotations

from pydantic import Field

from ...wenum.faction import FactionEnum
from .base import BaseModelWithAlias
from .reward import Reward


class MissionInfo(BaseModelWithAlias):
    """入侵任务详情 / Invasion Mission Info

    对应 Java: MissionInfo（独立文件）
    注意：与 Alert.MissionInfo 是不同的类。
    用于 Invasion.attacker_mission_info / Invasion.defender_mission_info。
    """

    seed: int | None = Field(default=None, alias="seed")
    faction: FactionEnum | None = Field(default=None, alias="faction")
    mission_reward: list[Reward] = Field(default_factory=list, alias="missionReward")

