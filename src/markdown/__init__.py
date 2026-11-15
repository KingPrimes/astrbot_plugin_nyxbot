"""Markdown 文本格式化器 / Markdown Text Formatters

现在只保留帮助消息的格式化器（:mod:`src.markdown.help`）——其余指令
（警报 / 突击 / 奸商等）统一用图片卡片回复（用户反馈 Markdown 文本
在 QQ 里展示臃肿），市场类指令的展示方式另行调整。

Only the help formatter remains here; every data command replies with its
image card instead of Markdown text.
"""
from __future__ import annotations

from .help import format_help_markdown

__all__ = ["format_help_markdown"]
