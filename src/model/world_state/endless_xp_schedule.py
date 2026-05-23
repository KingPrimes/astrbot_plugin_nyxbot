"""
EndlessXpSchedule Model / 双衍王境奖励排期模型

对应 API 字段: EndlessXpSchedule
包含 Activation、Expiry、CategoryChoices（同 EndlessXpChoices 结构）。
"""
from __future__ import annotations

from pydantic import Field

from .base import BaseModelWithAlias, DateField
from .endless_xp_choices import EndlessXpChoices as CategoryChoice


class EndlessXpSchedule(BaseModelWithAlias):
    """双衍王境奖励排期 / Duviri Endless XP Schedule"""

    activation: DateField | None = Field(default=None, alias="Activation")
    expiry: DateField | None = Field(default=None, alias="Expiry")
    category_choices: list[CategoryChoice] = Field(default_factory=list, alias="CategoryChoices")

