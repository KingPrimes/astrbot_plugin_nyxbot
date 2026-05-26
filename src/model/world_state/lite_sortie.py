"""
LiteSortie Model / 执刑官猎杀模型

对应 Java: LiteSortie.java
继承 BastWorldState，包含 Reward、Seed、Boss（BossEnum）、Missions（list[Mission]）。
"""
from __future__ import annotations

from pydantic import Field

from ...wenum.world_state import BossEnum
from .base import BastWorldState
from .mission import Mission


class LiteSortie(BastWorldState):
    """执刑官猎杀 / Archon Hunt (Lite Sortie)

    对应 Java: LiteSortie extends BastWorldState
    """

    reward: str | None = Field(default=None, alias="Reward")
    seed: int | None = Field(default=None, alias="Seed")
    boss: BossEnum | None = Field(default=None, alias="Boss")
    missions: list[Mission] = Field(default_factory=list, alias="Missions")

