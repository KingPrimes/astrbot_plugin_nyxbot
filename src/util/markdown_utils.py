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

#: 能把 Markdown 文本渲染成富文本的平台（AstrBot 平台名）。
#:
#: 只收录**有明确依据**的平台，未知平台一律视为不支持——宁可发图，
#: 也不要把 ``**`` / ``#`` 原样甩给用户：
#:
#: - ``qq_official`` / ``qq_official_webhook``：适配器按 ``msg_type=2`` 发送
#:   ``markdown.content``，Markdown 权限需内邀开通（``docs/qq-official-bot.md``
#:   §5.2 / §7.1），未开通时由适配器回退纯文本。
#: - ``telegram``：适配器先经 ``telegramify_markdown`` 转换，再以
#:   ``parse_mode="MarkdownV2"`` 发送。
#: - ``discord``：客户端自身渲染 Markdown，正文即富文本。
MARKDOWN_CAPABLE_PLATFORMS: frozenset[str] = frozenset(
    {
        "qq_official",
        "qq_official_webhook",
        "telegram",
        "discord",
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
