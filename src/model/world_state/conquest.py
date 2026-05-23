"""
Conquest Model / 征服模型

对应 Java: Conquest.java
继承 BastWorldState，包含 Type、Missions、Variables、RandomSeed。
"""
from __future__ import annotations

from pydantic import Field

from .base import BastWorldState


class Conquest(BastWorldState):
    """征服 / Conquest

    对应 Java: Conquest extends BastWorldState
    """

    type: str | None = Field(default=None, alias="Type")
    missions: list[dict] = Field(default_factory=list, alias="Missions")
    variables: list[str] = Field(default_factory=list, alias="Variables")
    random_seed: int | None = Field(default=None, alias="RandomSeed")
