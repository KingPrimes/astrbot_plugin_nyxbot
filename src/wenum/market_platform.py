"""
Market Platform Enum / Market 支持平台枚举
"""
from __future__ import annotations

from enum import StrEnum


class MarketPlatformEnum(StrEnum):
    """Market 支持平台枚举 — value = 平台标识字符串"""

    PC = "pc"
    PS4 = "ps4"
    XBOX = "xbox"
    SWITCH = "switch"
    MOBILE = "mobile"
