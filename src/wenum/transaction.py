"""
Transaction Enum / 交易类型枚举
"""
from __future__ import annotations

from enum import StrEnum


class TransactionEnum(StrEnum):
    """交易类型枚举 — value = 交易方向标识字符串"""

    SELL = "sell"
    BUY = "buy"
    ALL = "all"
    NONE = "none"
