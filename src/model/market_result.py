"""
MarketResult Model / 市场搜索结果模型

对应 Java: MarketResult.java
"""
from __future__ import annotations

from typing import Generic, TypeVar

from .base import BaseModelWithAlias

E = TypeVar("E")
R = TypeVar("R")


class MarketResult(BaseModelWithAlias, Generic[E, R]):
    """市场搜索结果容器"""

    entity: E | None = None
    result: R | None = None
    possible_items: list[str] = []
