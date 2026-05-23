"""
SyndicateMission Model / 集团任务模型

对应 Java: SyndicateMission.java
继承 BastWorldState，包含 Tag（SyndicateEnum）、Seed、Nodes、Jobs。
"""
from __future__ import annotations

from pydantic import Field

from ...wenum.world_state import SyndicateEnum
from .base import BastWorldState
from .job import Job


class SyndicateMission(BastWorldState):
    """集团任务 / Syndicate Mission

    对应 Java: SyndicateMission extends BastWorldState
    """

    tag: SyndicateEnum | None = Field(default=None, alias="Tag")
    seed: int | None = Field(default=None, alias="Seed")
    nodes: list[str] = Field(default_factory=list, alias="Nodes")
    jobs: list[Job] = Field(default_factory=list, alias="Jobs")

