"""
VoidStorms Model / 虚空风暴模型

对应 Java: VoidStorms.java
继承 BastWorldState，包含 Node、ActiveMissionTier（VoidEnum）。
"""
from __future__ import annotations

from pydantic import Field

from ...wenum.world_state import VoidEnum
from .base import BastWorldState


class VoidStorms(BastWorldState):
    """虚空风暴 / Void Storms (Railjack)

    对应 Java: VoidStorms extends BastWorldState
    """

    node: str | None = Field(default=None, alias="Node")
    tier: VoidEnum | None = Field(default=None, alias="ActiveMissionTier")

