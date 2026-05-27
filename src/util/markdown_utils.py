"""Platform detection utilities for QQ Official bot.

Used by the global on_decorating_result hook to determine
whether to apply platform-specific message formatting.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from astrbot.api.event import AstrMessageEvent

QQ_OFFICIAL_PLATFORMS = ("qq_official", "qq_official_webhook")


def is_qq_official(event: AstrMessageEvent) -> bool:
    """Check if the event originates from a QQ Official bot platform."""
    return event.get_platform_name() in QQ_OFFICIAL_PLATFORMS
