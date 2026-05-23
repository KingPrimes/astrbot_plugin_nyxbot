"""
PVPChallengeInstance Model / PVP 挑战实例模型

对应 API 字段: PVPChallengeInstances
不继承 BastWorldState（有自己的日期字段命名）。
"""
from __future__ import annotations

from pydantic import Field

from .base import BaseModelWithAlias, DateField, Id


class PVPChallengeInstance(BaseModelWithAlias):
    """PVP 挑战实例 / PVP Challenge Instance"""

    class Param(BaseModelWithAlias):
        """挑战参数 / Challenge Parameter"""
        n: str | None = None
        v: int | None = None
    id: Id | None = Field(default=None, alias="_id")
    challenge_type_ref_id: str | None = Field(default=None, alias="challengeTypeRefID")
    start_date: DateField | None = Field(default=None, alias="startDate")
    end_date: DateField | None = Field(default=None, alias="endDate")
    params: list[Param] = Field(default_factory=list, alias="params")
    is_generated: bool | None = Field(default=None, alias="isGenerated")
    pvp_mode: str | None = Field(default=None, alias="PVPMode")
    sub_challenges: list = Field(default_factory=list, alias="subChallenges")
    category: str | None = Field(default=None, alias="Category")

