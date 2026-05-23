"""
EndlessXpChoices Model / 双衍王境奖励模型

对应 Java: EndlessXpChoices.java
不继承 BastWorldState，包含 Category（枚举 EXC_NORMAL/EXC_HARD）和 Choices（奖励名称列表）。
用于 DuvalierCycle.choices。
"""
from __future__ import annotations

from enum import Enum

from pydantic import Field

from .base import BaseModelWithAlias


class CategoryEnum(Enum):
    """双衍王境奖励分类枚举 / Duviri Endless XP Category

    对应 Java: EndlessXpChoices.Category
    """
    EXC_NORMAL = "EXC_NORMAL"
    EXC_HARD = "EXC_HARD"


class EndlessXpChoices(BaseModelWithAlias):
    """双衍王境奖励 / Duviri Endless XP Choices

    对应 Java: EndlessXpChoices
    """

    category: CategoryEnum | None = Field(default=None, alias="Category")
    choices: list[str] = Field(default_factory=list, alias="Choices")

