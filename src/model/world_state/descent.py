"""
Descent Model / 深控下降模型

对应 Java: Descent.java
继承 BastWorldState，包含 RandSeed、Challenges（嵌套复杂结构）。
"""
from __future__ import annotations

from pydantic import Field

from .base import BastWorldState


class Descent(BastWorldState):
    """深控下降 / Descent (Deep Archimedea)

    对应 Java: Descent extends BastWorldState
    """

    rand_seed: int | None = Field(default=None, alias="RandSeed")
    challenges: list[dict] = Field(default_factory=list, alias="Challenges")
