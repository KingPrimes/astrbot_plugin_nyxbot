"""Ducats model / 杜卡币数据模型

对应 Java: io.github.kingprimes.model.Ducats
数据来源: https://api.warframe.market/v1/tools/ducats
"""
from __future__ import annotations

from enum import Enum

from pydantic import Field

from ..base import BaseModelWithAlias


class DumpType(str, Enum):
    """垃圾类型 — 镜像 Java Ducats.DumpType"""
    DAY = "当天"
    HOUR = "每小时"


class DucatItem(BaseModelWithAlias):
    """单条杜卡币数据 — 镜像 Java Ducats.Ducat"""
    datetime: str | None = Field(default=None)
    ducats: int | None = Field(default=None)
    ducats_per_platinum: float | None = Field(default=None, alias="ducats_per_platinum")
    ducats_per_platinum_wa: float | None = Field(default=None, alias="ducats_per_platinum_wa")
    id: str | None = Field(default=None)
    item: str = Field(default="")  # 物品 ID（内部），后续从数据库查名称
    item_name: str = Field(default="")  # 物品显示名称（由 service 填充）
    median: float | None = Field(default=None)
    plat_worth: float | None = Field(default=None, alias="plat_worth")
    position_change_day: int | None = Field(default=None, alias="position_change_day")
    position_change_week: int | None = Field(default=None, alias="position_change_week")
    position_change_month: int | None = Field(default=None, alias="position_change_month")
    volume: int | None = Field(default=None)
    wa_price: float | None = Field(default=None, alias="wa_price")



class DucatsPayload(BaseModelWithAlias):
    """杜卡币载荷"""
    previous_day: list[DucatItem] = Field(default_factory=list, alias="previous_day")
    previous_hour: list[DucatItem] = Field(default_factory=list, alias="previous_hour")



class Ducats(BaseModelWithAlias):
    """杜卡币数据 — 镜像 Java Ducats.java"""
    payload: DucatsPayload | None = Field(default=None)
