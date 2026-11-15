"""Help package / 帮助内容包

只导出**内容目录**（零依赖，渲染层也放心引）；发送方式判定在
``src.help.format``，因为它要读插件配置，不应被渲染层间接拉进来。

Only the dependency-free catalog is re-exported here; the delivery-format
resolver lives in :mod:`src.help.format` because it reads plugin config.
"""
from __future__ import annotations

from .catalog import (
    HELP_SUBTITLE,
    HELP_TITLE,
    HelpEntry,
    HelpSection,
    build_help_sections,
    command_usage,
)

__all__ = [
    "HELP_SUBTITLE",
    "HELP_TITLE",
    "HelpEntry",
    "HelpSection",
    "build_help_sections",
    "command_usage",
]
