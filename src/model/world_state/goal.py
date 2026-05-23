"""
Goal Model / 活动目标模型

对应 Java: Goal.java
继承 BastWorldState，包含 Node、ScoreVar、Count、HealthPct、Regions、Desc、Tooltip、
Tag、UpgradeIds、Reward（独立模型）、InterimGoals、InterimRewards、Faction、Icon 等。
"""
from __future__ import annotations

from pydantic import Field

from ...wenum.faction import FactionEnum
from .base import BastWorldState, Id
from .reward import Reward


class Goal(BastWorldState):
    """活动目标 / Event Goal

    对应 Java: Goal extends BastWorldState
    """

    node: str | None = Field(default=None, alias="Node")
    score_var: str | None = Field(default=None, alias="ScoreVar")
    score_loc_tag: str = Field(default="", alias="ScoreLocTag")
    count: int | None = Field(default=None, alias="Count")
    health_pct: float | None = Field(default=None, alias="HealthPct")
    regions: list[int] = Field(default_factory=list, alias="Regions")
    desc: str | None = Field(default=None, alias="Desc")
    tool_tip: str | None = Field(default=None, alias="Tooltip")
    optional_in_mission: bool | None = Field(default=None, alias="OptionalInMission")
    tag: str | None = Field(default=None, alias="Tag")
    upgrade_ids: list[Id] = Field(default_factory=list, alias="UpgradeIds")
    personal: bool | None = Field(default=None, alias="Personal")
    community: bool | None = Field(default=None, alias="Community")
    goal: int | None = Field(default=None, alias="Goal")
    reward: Reward | None = Field(default=None, alias="Reward")
    interim_goals: list[int] = Field(default_factory=list, alias="InterimGoals")
    interim_rewards: list[Reward] = Field(default_factory=list, alias="InterimRewards")
    bonus_reward: Reward | None = Field(default=None, alias="BonusReward")
    clan_goal: list[int] = Field(default_factory=list, alias="ClanGoal")
    faction: FactionEnum | None = Field(default=None, alias="Faction")
    icon: str | None = Field(default=None, alias="Icon")
    mission_key_name: str = Field(default="", alias="MissionKeyName")
    success: int | None = Field(default=None, alias="Success")

