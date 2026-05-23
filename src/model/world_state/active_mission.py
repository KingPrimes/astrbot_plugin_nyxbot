"""
ActiveMission Model / 裂隙任务模型

对应 Java: ActiveMission.java
继承 BastWorldState，包含 MissionType（MissionTypeEnum）、Modifier（VoidEnum）、
Faction（FactionEnum）、Node、Region、Seed、Hard、VoidStorms 等。
"""
from __future__ import annotations

from pydantic import Field

from ...wenum.faction import FactionEnum
from ...wenum.mission_type import MissionTypeEnum
from ...wenum.world_state import VoidEnum
from .base import BastWorldState


class ActiveMission(BastWorldState):
    """裂隙任务 / Void Fissure Mission (ActiveMission)

    对应 Java: ActiveMission extends BastWorldState
    """

    mission_type: MissionTypeEnum | None = Field(default=None, alias="MissionType")
    modifier: VoidEnum | None = Field(default=None, alias="Modifier")
    node: str | None = Field(default=None, alias="Node")
    faction: FactionEnum | None = Field(default=None, alias="Faction")
    region: int | None = Field(default=None, alias="Region")
    seed: int | None = Field(default=None, alias="Seed")
    hard: bool = Field(default=False, alias="Hard")
    void_storms: bool = Field(default=False, alias="voidStorms")

