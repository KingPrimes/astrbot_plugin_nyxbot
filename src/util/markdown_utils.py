"""Platform detection utilities for QQ Official bot.

Used by the global on_decorating_result hook to determine
whether to apply platform-specific message formatting.

本模块只回答「平台能不能渲染 Markdown」，不读配置、不碰业务：
用户是否**想**用 Markdown 由 ``qq_markdown_enabled`` 决定，
两者在 ``src/help/format.py`` 里合并成最终判定。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from astrbot.api.event import AstrMessageEvent

#: 能走本插件 Markdown 路径的平台（AstrBot 平台名）。
#:
#: **只收录 qq_official / qq_official_webhook**，未知平台一律视为不支持——
#: 宁可发图，也不要把排版原件甩给用户：
#:
#: - 本插件的 Markdown 形态是 QQ 官方专属的：帮助正文用 ``mqqapi://aio/inlinecmd``
#:   内联指令链接（点击填入 QQ 发送框）、``#宽px #高px`` 图片语法，WM 用
#:   QQ 方言的管道表格与内联键盘按钮——telegram / discord 虽能渲染基础
#:   Markdown，但链接点不动、表格不渲染、按钮被丢弃（2026-11-16 Sourcery
#:   评审指出，此前误收 telegram / discord）；
#: - ``qq_official`` / ``qq_official_webhook``：适配器按 ``msg_type=2`` 发送
#:   ``markdown.content``（``docs/qq-official-bot.md`` §5.2 / §7.1），
#:   未开通 Markdown 权限时由适配器回退纯文本。
#:
#: 若未来为其他平台做专属排版，应另建平台专属格式化器并扩充此表，
#: 而不是直接把 QQ 形态发出去。
MARKDOWN_CAPABLE_PLATFORMS: frozenset[str] = frozenset(
    {
        "qq_official",
        "qq_official_webhook",
    }
)


def supports_markdown(event: AstrMessageEvent) -> bool:
    """平台是否支持以 Markdown 消息发送 / Whether the platform renders Markdown.

    Args:
        event: 任意消息事件。

    Returns:
        ``True`` 表示可以把 Markdown 原文交给平台渲染；
        ``False`` 表示应改用图片等富文本替代方案。
    """
    return event.get_platform_name() in MARKDOWN_CAPABLE_PLATFORMS
