"""
Market Status Enum / Market 用户在线状态枚举
"""
from __future__ import annotations

from enum import StrEnum


class MarketStatusEnum(StrEnum):
    """Market 用户在线状态枚举 — value = 成员名称字符串"""

    INVISIBLE = ("INVISIBLE", "不可见")
    OFFLINE = ("OFFLINE", "离线")
    ONLINE = ("ONLINE", "在线")
    INGAME = ("INGAME", "游戏中")

    def __new__(cls, value: str, display_name: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj._display_name = display_name  # type: ignore
        return obj

    @property
    def display_name(self) -> str:
        """在线状态中文名称"""
        return self._display_name  # type: ignore
