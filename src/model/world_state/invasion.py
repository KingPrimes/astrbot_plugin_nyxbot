"""
Invasion Model / 入侵任务模型

对应 Java: Invasion.java
继承 BastWorldState，包含进攻方/防守方阵营、奖励及任务信息。

注意：API 中 AttackerReward 有时是单个对象、有时是数组，用 field_validator 统一转为 list。
"""
from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from ...wenum.faction import FactionEnum
from .base import BastWorldState, Id
from .mission_info import MissionInfo
from .reward import Reward


class Invasion(BastWorldState):
    """入侵任务 / Invasion Mission

    对应 Java: Invasion extends BastWorldState
    """

    faction: FactionEnum | None = Field(default=None, alias="Faction")
    defender_faction: FactionEnum | None = Field(default=None, alias="DefenderFaction")
    node: str | None = Field(default=None, alias="Node")
    count: float | None = Field(default=None, alias="Count")
    goal: float | None = Field(default=None, alias="Goal")
    loc_tag: str | None = Field(default=None, alias="LocTag")
    completed: bool | None = Field(default=None, alias="Completed")
    chain_id: Id | None = Field(default=None, alias="ChainID")
    attacker_reward: list[Reward] = Field(default_factory=list, alias="AttackerReward")
    attacker_mission_info: MissionInfo | None = Field(default=None, alias="AttackerMissionInfo")
    defender_reward: Reward | None = Field(default=None, alias="DefenderReward")
    defender_mission_info: MissionInfo | None = Field(default=None, alias="DefenderMissionInfo")

    @field_validator("attacker_reward", mode="before")
    @classmethod
    def _normalize_attacker_reward(cls, v: Any) -> list[Any]:
        """API 可能返回单个对象或数组，统一转为列表 / Normalize single object or array to list"""
        if v is None:
            return []
        if isinstance(v, dict):
            return [v]
        if isinstance(v, list):
            return v
        return []

