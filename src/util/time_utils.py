"""Time utilities / 时间处理工具

提供 Warframe 世界状态中常见时间格式的解析和显示功能。
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional


def parse_wf_timestamp(timestamp_str: str) -> Optional[datetime]:
    """解析 Warframe API 返回的时间戳字符串。

    Warframe 世界状态使用 ISO 8601 格式的时间戳，例如：
    "2025-01-15T12:00:00.000Z"

    Args:
        timestamp_str: 时间戳字符串。

    Returns:
        解析后的 datetime 对象（UTC），解析失败返回 None。
    """
    try:
        # 处理末尾的 Z 表示 UTC
        if timestamp_str.endswith("Z"):
            timestamp_str = timestamp_str[:-1] + "+00:00"
        return datetime.fromisoformat(timestamp_str)
    except (ValueError, AttributeError):
        return None


def format_time_remaining(expiry: datetime, now: Optional[datetime] = None) -> str:
    """计算并格式化剩余时间。

    Args:
        expiry: 到期时间（UTC）。
        now: 当前时间（UTC），默认为 datetime.now(timezone.utc)。

    Returns:
        格式化后的剩余时间字符串，如 "2小时30分钟"、"已过期"。
    """
    if now is None:
        now = datetime.now(timezone.utc)

    remaining = expiry - now

    if remaining.total_seconds() <= 0:
        return "已过期"

    total_seconds = int(remaining.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    if hours > 0:
        return f"{hours}小时{minutes}分钟"
    else:
        return f"{minutes}分钟"


def format_time_remaining_short(expiry: datetime, now: Optional[datetime] = None) -> str:
    """简短格式的剩余时间。

    Args:
        expiry: 到期时间（UTC）。
        now: 当前时间（UTC）。

    Returns:
        简短格式，如 "2h 30m"、"已过期"。
    """
    if now is None:
        now = datetime.now(timezone.utc)

    remaining = expiry - now

    if remaining.total_seconds() <= 0:
        return "已过期"

    total_seconds = int(remaining.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


def is_expired(timestamp_str: str) -> bool:
    """判断 Warframe 时间戳是否已过期。

    Args:
        timestamp_str: Warframe API 返回的时间戳字符串。

    Returns:
        是否已过期。
    """
    expiry = parse_wf_timestamp(timestamp_str)
    if expiry is None:
        return True
    return expiry < datetime.now(timezone.utc)
