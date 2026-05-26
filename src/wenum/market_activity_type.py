"""
Market Activity Type Enum / Market 用户活动状态枚举
"""
from __future__ import annotations

from enum import StrEnum, unique


@unique
class MarketActivityTypeEnum(StrEnum):
    """Market 用户活动状态枚举 — value = 成员名称字符串"""

    UNKNOWN = ("UNKNOWN", "未知")
    IDLE = ("IDLE", "空闲")
    ON_MISSION = ("ON_MISSION", "任务中")
    IN_DOJO = ("IN_DOJO", "在道场")
    IN_ORBITER = ("IN_ORBITER", "在轨道器")
    IN_RELAY = ("IN_RELAY", "在中继站")

    def __new__(cls, value: str, display_name: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj._display_name = display_name  # type: ignore
        return obj

    @property
    def display_name(self) -> str:
        """活动状态中文名称"""
        return self._display_name  # type: ignore
