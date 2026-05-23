"""
SeasonInfo Model / 午夜电波模型

对应 Java: SeasonInfo.java
继承 BastWorldState，包含 AffiliationTag、Season、Phase、Params、ActiveChallenges（嵌套类）。
"""
from __future__ import annotations

from pydantic import Field

from .base import BaseModelWithAlias, BastWorldState, Id


class SeasonInfo(BastWorldState):
    """午夜电波赛季信息 / Nightwave Season Info

    对应 Java: SeasonInfo extends BastWorldState
    """

    class ActiveChallenges(BaseModelWithAlias):
        """活跃挑战 / Active Challenge

        Java: SeasonInfo.ActiveChallenges
        """
        _id: Id | None = None
        challenge: str | None = Field(default=None, alias="Challenge")
        name: str | None = Field(default=None, alias="Name")
        description: str | None = Field(default=None, alias="Description")
        standing: int | None = Field(default=None, alias="Standing")
        required: int | None = Field(default=None, alias="Required")
        daily: bool | None = Field(default=None, alias="Daily")
        weekly: bool | None = Field(default=None, alias="Weekly")
        elite: bool | None = Field(default=None, alias="Elite")
    affiliation_tag: str | None = Field(default=None, alias="AffiliationTag")
    season: int | None = Field(default=None, alias="Season")
    phase: int | None = Field(default=None, alias="Phase")
    params: str | None = Field(default=None, alias="Params")
    active_challenges: list[ActiveChallenges] = Field(default_factory=list, alias="ActiveChallenges")

