"""Markdown 文本格式化器 / Markdown Text Formatters

在 QQ 官方平台替代图片卡片，将数据模型格式化为 Markdown 文本。
"""
from __future__ import annotations

from .alerts import format_alerts_markdown
from .daily_deals import format_daily_deals_markdown
from .lite_sortie import format_lite_sorties_markdown
from .sorties import format_sorties_markdown
from .void_trader import format_void_trader_markdown

__all__ = [
    "format_alerts_markdown",
    "format_daily_deals_markdown",
    "format_lite_sorties_markdown",
    "format_sorties_markdown",
    "format_void_trader_markdown",
]
