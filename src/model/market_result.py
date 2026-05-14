"""
MarketResult Model / 市场搜索结果模型

对应 Java: MarketResult.java
"""
from __future__ import annotations

from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel

E = TypeVar("E")
R = TypeVar("R")


class MarketResult(BaseModel, Generic[E, R]):
    """市场搜索结果容器"""

    entity: Optional[E] = None
    result: Optional[R] = None
    possible_items: List[str] = []
