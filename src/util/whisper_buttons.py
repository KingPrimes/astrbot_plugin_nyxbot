"""市场卡片私聊语句快捷按钮 / Whisper quick-pick buttons

MD 版市场订单卡片底部的序号按钮：点击后机器人回复对应**表格行号**的
私聊语句（与 ``/w 行号`` 完全一致，走 ``whisper_service`` 的同一份
2 分钟缓存），用户长按复制粘贴进游戏。QQ 没有真正的"复制到剪贴板"
按钮能力，「点击 → 回文本 → 长按复制」是最接近的交互。

按钮 id 前缀 ``nyxbot:w:``，回调数据 ``{"cmd": "w", "n": "<行号>"}``；
点击路由见 ``wf_whisper`` 的 ``button_action`` 处理器。行号与 Markdown
表格 / 图片卡片最左列一致（对齐 ``orders`` 全量编号），只为有私聊语句的
行出按钮——卖家未公开游戏名的占位行不出按钮，序号也不会错位。
CD/XT/WR 的 MD 版可直接复用本构建器。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import astrbot.api.message_components as Comp

from .framework_caps import BUTTONS_AVAILABLE

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
    rows: Sequence[tuple[int, int | None]], token: str = ""
) -> list[Comp.ActionRow]:
    """生成序号取句按钮行 / Build the whisper pick buttons.

    Args:
        rows: ``(表格行号, 价格)`` 对——只为**有私聊语句**的行出按钮；
            行号即卡片表格的行号（点击回该行的私聊语句），价格拼进标签
            免去来回对照，为 ``None`` 时标签退化为纯行号。
        token: 结果指纹（``whisper_service.remember`` 的返回值）——拼进
            回调数据，旧卡片的按钮在新查询覆盖缓存后可被识别并提示
            重新查询，而不是悄悄返回新结果的语句。

    Returns:
        ``ActionRow`` 列表（每行 :data:`BUTTONS_PER_ROW` 个，总按钮数不超过
        ``MAX_ROWS * BUTTONS_PER_ROW``）；当前 AstrBot 不支持按钮（组件或
        回调装饰器任一缺失）时返回空列表。
    """
    if not rows or not BUTTONS_AVAILABLE:
        return []

    capped = rows[: MAX_ROWS * BUTTONS_PER_ROW]
    buttons: list[Comp.Button] = []
    for row_number, price in capped:
        label = f"{row_number}·{price}p" if price is not None else str(row_number)
        buttons.append(
            Comp.Button(
                id=f"{WHISPER_BUTTON_PREFIX}{row_number}",
                label=label,
                action=Comp.Button.CallbackAction(
                    data={"cmd": "w", "n": str(row_number), "k": token}
                ),
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
