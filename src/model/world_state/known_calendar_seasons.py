"""
KnownCalendarSeasons Model / 1999 日历季节模型

对应 Java: KnownCalendarSeasons.java
继承 BastWorldState，包含 Days、Season（SeasonEnum）、YearIteration、Version 等。

包含嵌套枚举: DaysTypeEnum (CET_CHALLENGE/CET_REWARD/CET_UPGRADE)、SeasonEnum (四季)
包含嵌套类: Days、Events、Events.Challenge (record)、Events.Upgrade (record)
"""
from __future__ import annotations

from enum import Enum

from pydantic import Field

from .base import BaseModelWithAlias, BastWorldState


class DaysTypeEnum(Enum):
    """日期事件类型枚举 / Days Type Enum

    对应 Java: KnownCalendarSeasons.DaysTypeEnum
    """
    CET_CHALLENGE = "任务"
    CET_REWARD = "奖励"
    CET_UPGRADE = "加成"

    @classmethod
    def _missing_(cls, value):
        """支持通过成员名称字符串匹配枚举。

        API 返回英文枚举名如 "CET_CHALLENGE"，但 .value 是中文。
        """
        if isinstance(value, str):
            try:
                return cls[value]
            except KeyError:
                pass
        return None


class SeasonEnum(Enum):
    """季节枚举 / Season Enum

    对应 Java: KnownCalendarSeasons.SeasonEnum
    """
    CST_FALL = "秋季"
    CST_SUMMER = "夏季"
    CST_SPRING = "春季"
    CST_WINTER = "冬季"

    @classmethod
    def _missing_(cls, value):
        """支持通过成员名称字符串匹配枚举。

        API 返回英文枚举名如 "CST_SUMMER"，但 .value 是中文。
        """
        if isinstance(value, str):
            try:
                return cls[value]
            except KeyError:
                pass
        return None


class KnownCalendarSeasons(BastWorldState):
    """1999 日历季节 / Known Calendar Seasons

    对应 Java: KnownCalendarSeasons extends BastWorldState
    """

    class Events(BaseModelWithAlias):
        """日历事件 / Calendar Event

        Java: KnownCalendarSeasons.Events
        """
        type: DaysTypeEnum | None = Field(default=None, alias="type")
        reward: str | None = Field(default=None, alias="reward")
        challenge: str | None = Field(default=None, alias="challenge")
        challenge_info: dict | None = Field(default=None, alias="challengeInfo")  # Challenge record
        upgrade_info: dict | None = Field(default=None, alias="upgradeInfo")  # Upgrade record
        upgrade: str | None = Field(default=None, alias="upgrade")
    class Days(BaseModelWithAlias):
        """日期 / Day

        Java: KnownCalendarSeasons.Days
        """
        day: int | None = Field(default=None, alias="day")
        events: list[KnownCalendarSeasons.Events] = Field(default_factory=list, alias="events")
        month: int | None = Field(default=None, alias="month")
    days: list[Days] = Field(default_factory=list, alias="Days")
    season: SeasonEnum | None = Field(default=None, alias="Season")
    year_iteration: int | None = Field(default=None, alias="YearIteration")
    version: int | None = Field(default=None, alias="Version")
    upgrade_availability_requirements: list[str] = Field(default_factory=list, alias="UpgradeAvaliabilityRequirements")
    month_days: dict | None = Field(default=None, alias="MonthDays")

