"""
Mission Model / 任务详情模型

对应 Java: Mission.java
不继承 BastWorldState，包含 missionType（MissionTypeEnum）和 node。
"""
from __future__ import annotations

from pydantic import Field

from ...wenum.mission_type import MissionTypeEnum
from .base import BaseModelWithAlias


class Mission(BaseModelWithAlias):
    """任务详情 / Mission Detail

    对应 Java: Mission
    用于 LiteSorite（执刑官猎杀）的 missions 列表。
    """

    mission_type: MissionTypeEnum | None = Field(default=None, alias="missionType")
    node: str | None = Field(default=None, alias="node")

