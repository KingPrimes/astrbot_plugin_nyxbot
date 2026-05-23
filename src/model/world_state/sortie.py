"""
Sortie Model / 突击任务模型

对应 Java: Sortie.java
继承 BastWorldState，包含 Boss（BossEnum）、Variants（list[Variant]）、ExtraDrops 等。
"""
from __future__ import annotations

from pydantic import Field

from ...wenum.world_state import BossEnum
from .base import BastWorldState
from .variant import Variant


class Sortie(BastWorldState):
    """突击任务 / Sortie Mission

    对应 Java: Sortie extends BastWorldState
    """

    boss: BossEnum | None = Field(default=None, alias="Boss")
    reward: str | None = Field(default=None, alias="Reward")
    seed: int | None = Field(default=None, alias="Seed")
    variants: list[Variant] = Field(default_factory=list, alias="Variants")
    twitter: bool | None = Field(default=None, alias="Twitter")
    extra_drops: list[str] = Field(default_factory=list, alias="ExtraDrops")

