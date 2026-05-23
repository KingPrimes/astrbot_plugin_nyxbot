"""
ScheduleInfo Model / 瓦奇娅时间表模型

对应 Java: ScheduleInfo.java
继承 BastWorldState，包含 FeaturedItem 字段。
用于 PrimeVaultTrader.schedule_infos。
"""
from __future__ import annotations

from pydantic import Field

from .base import BastWorldState, DateField


class ScheduleInfo(BastWorldState):
    """瓦奇娅时间表 / Prime Vault Schedule Info

    对应 Java: ScheduleInfo extends BastWorldState
    """

    item: str | None = Field(default=None, alias="FeaturedItem")
    preview_hidden_until: DateField | None = Field(default=None, alias="PreviewHiddenUntil")

