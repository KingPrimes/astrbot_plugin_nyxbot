"""
Variant Model / 突击阶段任务模型

对应 Java: Variant.java
不继承 BastWorldState，包含 missionType、modifierType、node、tileset。
用于 Sortie（突击任务）的 variants 列表。
"""
from __future__ import annotations

from pydantic import Field

from ...wenum.mission_type import MissionTypeEnum
from ...wenum.world_state import ModifierTypeEnum
from .base import BaseModelWithAlias


class Variant(BaseModelWithAlias):
    """突击阶段任务 / Sortie Variant

    对应 Java: Variant
    用于 Sortie.variants 列表。
    """

    mission_type: MissionTypeEnum | None = Field(default=None, alias="missionType")
    modifier_type: ModifierTypeEnum | None = Field(default=None, alias="modifierType")
    node: str | None = Field(default=None, alias="node")
    tileset: str | None = Field(default=None, alias="tileset")

