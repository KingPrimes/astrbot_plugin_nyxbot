"""帮助消息发送方式判定 / Help delivery format resolution

帮助内容有两种发送方式，切换条件（**只作用于帮助指令**）：

============================  ==============================================
条件                          发送方式
============================  ==============================================
开关开启 + 平台支持 Markdown  Markdown 文本（``# 标题`` + ``- **指令** — 说明``）
开关关闭                      图片卡片（``src/render/card_help.py``）
开关开启 + 平台不支持 Markdown 图片卡片（同一份内容降级出图）
============================  ==============================================

开关即配置项 ``qq_markdown_enabled``（「使用 Markdown 进行回复」）。
平台能力见 :data:`src.util.markdown_utils.MARKDOWN_CAPABLE_PLATFORMS`。

The switch is the user-facing "reply with Markdown" option; the platform
capability table decides whether Markdown can actually be rendered. Either
condition failing degrades to the image card holding identical content.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from astrbot.api import logger

from ..config.config import get_qq_markdown_enabled
from ..util.markdown_utils import supports_markdown

if TYPE_CHECKING:
    from astrbot.api.event import AstrMessageEvent

#: 帮助消息的发送方式：Markdown 文本 或 图片。
HelpFormat = Literal["markdown", "image"]


def resolve_help_format(event: AstrMessageEvent) -> HelpFormat:
    """判定本次帮助该走 Markdown 还是图片 / Decide how to deliver the help.

    判定顺序（先开关、后平台能力，前者是用户意图，后者是客观限制）：

    1. ``qq_markdown_enabled`` 关闭 → ``"image"``（用户没要求 Markdown）；
    2. 平台不在 Markdown 能力表内 → ``"image"``（发出去只会看到 ``**`` 原文）；
    3. 其余 → ``"markdown"``。

    Args:
        event: 触发本次帮助的消息事件。

    Returns:
        ``"markdown"`` 或 ``"image"``。
    """
    platform = event.get_platform_name()
    if not get_qq_markdown_enabled():
        logger.debug(f"帮助发送方式: 图片（Markdown 开关关闭，平台={platform}）")
        return "image"
    if not supports_markdown(event):
        logger.debug(f"帮助发送方式: 图片（平台 {platform} 不支持 Markdown）")
        return "image"
    logger.debug(f"帮助发送方式: Markdown（平台={platform}）")
    return "markdown"
