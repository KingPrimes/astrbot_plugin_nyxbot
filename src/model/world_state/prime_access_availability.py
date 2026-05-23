"""
PrimeAccessAvailability Model / Prime Access 可用性模型

对应 API 字段: PrimeAccessAvailability
不继承 BastWorldState。
"""
from __future__ import annotations

from pydantic import Field

from .base import BaseModelWithAlias


class PrimeAccessAvailability(BaseModelWithAlias):
    """Prime Access 可用性 / Prime Access Availability"""

    state: str | None = Field(default=None, alias="State")

