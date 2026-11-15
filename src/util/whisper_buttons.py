"""市场卡片私聊语句快捷按钮 / Whisper quick-pick buttons

MD 版市场订单卡片底部的序号按钮：点击后机器人回复对应序号的私聊语句
（与 ``/w 序号`` 完全一致，走 ``whisper_service`` 的同一份 2 分钟缓存），
用户长按复制粘贴进游戏。QQ 没有真正的"复制到剪贴板"按钮能力，
「点击 → 回文本 → 长按复制」是最接近的交互。

按钮 id 前缀 ``nyxbot:w:``，回调数据 ``{"cmd": "w", "n": "<序号>"}``；
点击路由见 ``wf_whisper`` 的 ``button_action`` 处理器。
CD/XT/WR 的 MD 版可直接复用本构建器。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import astrbot.api.message_components as Comp

if TYPE_CHECKING:
    from collections.abc import Sequence

#: 私聊取句按钮 id 前缀：``nyxbot:w:<序号>``。
WHISPER_BUTTON_PREFIX = "nyxbot:w:"

#: 与帮助按钮一致的布局参数（4 列，最多 5 行）。
BUTTONS_PER_ROW = 4
MAX_ROWS = 5

#: 键盘不可用时的文字兜底（平台自身不支持按钮时由适配器使用）。
FALLBACK_TEXT = "点击按钮获取对应序号的私聊语句（2 分钟内有效）。"


def build_whisper_buttons(
    count: int, prices: Sequence[int | None]
) -> list[Comp.ActionRow]:
    """生成序号取句按钮行 / Build the whisper pick buttons.

    Args:
        count: 按钮数量（与缓存里的私聊语句条数一致，保证点击必有结果）。
        prices: 各序号对应的价格（拼进标签，免去来回对照列表）；
            不足或为 ``None`` 时标签退化为纯序号。

    Returns:
        ``ActionRow`` 列表（每行 :data:`BUTTONS_PER_ROW` 个）；当前 AstrBot
        不支持按钮组件时返回空列表。
    """
    if count <= 0 or not hasattr(Comp, "ActionRow") or not hasattr(Comp, "Button"):
        return []

    capped = min(count, MAX_ROWS * BUTTONS_PER_ROW)
    buttons: list[Comp.Button] = []
    for index in range(capped):
        price = prices[index] if index < len(prices) else None
        label = f"{index + 1}·{price}p" if price is not None else str(index + 1)
        buttons.append(
            Comp.Button(
                id=f"{WHISPER_BUTTON_PREFIX}{index + 1}",
                label=label,
                action=Comp.Button.CallbackAction(data={"cmd": "w", "n": str(index + 1)}),
                style=Comp.Button.Style.PRIMARY,
            )
        )

    return [
        Comp.ActionRow(
            buttons=buttons[index : index + BUTTONS_PER_ROW],
            fallback_text=FALLBACK_TEXT,
        )
        for index in range(0, len(buttons), BUTTONS_PER_ROW)
    ]
