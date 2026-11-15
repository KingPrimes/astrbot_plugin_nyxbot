"""帮助消息的可点击按钮 / Interactive buttons for the help message

把帮助条目排成 QQ 内联键盘（AstrBot 的可移植 ``ActionRow``）：点一下按钮，
平台回传一个 ``ButtonInteraction``，由 ``src/commands/wf_help.py`` 里的
``button_action`` 处理器路由到对应指令。

按钮**默认只收可直接执行的指令**（无需参数，主色）——需要参数的指令由
``mqqapi`` 内联链接承载（点击自动把指令填入发送框，比按钮回提示更友好，
见 ``src/markdown/help.py``）；链接菜单关闭时传 ``include_params=True``，
参数指令以成功色按钮兜底（点击只回用法提示）。

约束（QQ 官方 / AstrBot 双侧，见 ``docs/qq-official-bot.md`` §7.3）：

- 单条消息最多 **5 行 × 每行 5 个**按钮；
- ``label`` 最多 **10 个字符**；
- 按钮 ``id`` 在同一条消息内必须**唯一**（AstrBot 会校验并抛错），
  因此每条指令的 id 都带指令名后缀，回调侧用前缀识别归属；
- 按钮只随 Markdown 消息发送——图片卡片路径不带按钮。

The keyboard is capped at 5x5 buttons with unique per-message ids; only the
Markdown delivery path carries it. By default only argument-free commands get
buttons; parameterised ones fall back to buttons only when the inline link
menu is disabled.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import astrbot.api.message_components as Comp
from astrbot.api import logger

from ..util.framework_caps import BUTTONS_AVAILABLE

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .catalog import HelpEntry, HelpSection

#: 帮助按钮 id 前缀：``nyxbot:help:<指令名>``。
#: 回调按前缀判断归属，避免误吃其它插件/功能的按钮点击。
HELP_BUTTON_PREFIX = "nyxbot:help:"

#: QQ 内联键盘上限：5 行，每行最多 5 个。
MAX_BUTTONS_PER_ROW = 5
MAX_ROWS = 5

#: 实际每行按钮数。5 列会把「仲裁表」这类三字标签挤成「仲…」，
#: 4 列更宽、可读性更好；行数上限同步收敛，总按钮数不变。
BUTTONS_PER_ROW = 4

#: 「长标签」阈值：超过 2 个文字的按钮一行 2 列（每个约占半行宽，
#: 4~5 字标签不再截断）；**数字按钮不参与该规则**——数字字符窄，
#: 4 列也完整显示（如 ``1999``）。
LONG_LABEL_THRESHOLD = 2
LONG_BUTTONS_PER_ROW = 2

#: 键盘不可用时的文字兜底（平台自身不支持按钮时由适配器使用）。
FALLBACK_TEXT = "当前平台不支持按钮，请直接发送上面的指令。"


def is_help_button(action_id: str) -> bool:
    """按钮回调是否属于帮助消息 / Whether the click came from a help button."""
    return action_id.startswith(HELP_BUTTON_PREFIX)


def command_from_action_id(action_id: str) -> str:
    """从按钮 id 里取回指令名 / Extract the bare command from a button id."""
    return action_id.removeprefix(HELP_BUTTON_PREFIX).strip()


def _is_long_label(command: str) -> bool:
    """是否需要 2 列宽度的长标签按钮 / Whether the label needs a wide button.

    超过 2 个文字即视为长标签；纯数字按钮（如 ``1999``）不参与该规则。
    """
    return len(command) > LONG_LABEL_THRESHOLD and not command.isdigit()


def _make_button(entry: HelpEntry) -> Comp.Button:
    """按条目构建一个按钮 / Build one button for an entry.

    样式按能力区分：参数指令用成功色（仅 ``include_params`` 兜底模式
    会出现），无参数指令用主色。
    """
    return Comp.Button(
        id=f"{HELP_BUTTON_PREFIX}{entry.command}",
        label=entry.command,
        action=Comp.Button.CallbackAction(data={"cmd": entry.command}),
        style=(
            Comp.Button.Style.SUCCESS
            if entry.arg_hint
            else Comp.Button.Style.PRIMARY
        ),
    )


def count_button_eligible(
    sections: Sequence[HelpSection], include_params: bool = False
) -> int:
    """统计应进按钮的条目数 / Count entries eligible for a button slot.

    与 :func:`build_help_buttons` 的筛选口径一致（``include_params`` 决定
    参数指令是否计入），供调用方判断键盘是否装下了全部条目。
    """
    return sum(
        1
        for section in sections
        for entry in section.entries
        if entry.button and (include_params or not entry.arg_hint)
    )


def buttons_truncated(
    sections: Sequence[HelpSection],
    rows: Sequence[Comp.ActionRow],
    include_params: bool = False,
) -> bool:
    """按钮是否因键盘行数上限被截断 / Whether the keyboard dropped entries.

    ``True`` 表示有应进按钮的指令没有按钮位——调用方应让正文覆盖这些
    指令（回退完整分节列表），避免它们在帮助消息里彻底不可见。
    """
    placed = sum(len(row.buttons) for row in rows)
    return placed < count_button_eligible(sections, include_params)


def build_help_buttons(
    sections: Sequence[HelpSection], include_params: bool = False
) -> list[Comp.ActionRow]:
    """按帮助分节生成按钮行 / Build the inline keyboard rows.

    布局分两步：

    - **能力筛选**：默认只收可直接执行的指令（无需参数）——参数指令由
      ``mqqapi`` 内联链接承载（点击自动填入发送框）；``include_params=True``
      时（链接菜单关闭的兜底场景）参数指令也进按钮，点击只回用法提示。
    - **宽度分组**：长标签（>2 字，数字除外）一行 2 列，其余一行 4 列；
      短组在前保持目录开头的顺序。总行数受 QQ 5 行上限约束，超出截断
      并打告警日志（兜底模式 18 条目会占 7 行，必截断——调用方应据
      :func:`buttons_truncated` 回退完整正文，保证内容不缺）。

    Args:
        sections: :func:`src.help.catalog.build_help_sections` 的返回值。
        include_params: 是否把需要参数的指令也排进按钮（兜底模式）。

    Returns:
        ``ActionRow`` 列表（最多 :data:`MAX_ROWS` 行）；当前 AstrBot 不支持
        按钮（组件或回调装饰器任一缺失）时返回空列表，调用方退化为纯文本
        帮助——能力探测统一取自 ``src.util.framework_caps``，避免与
        ``registry`` 的回调注册探测不同步而发出死按钮。
    """
    if not BUTTONS_AVAILABLE:
        return []

    # 先摊平再分组切块：行数/每行数量都由上限决定，不依赖分节边界
    entries = [entry for section in sections for entry in section.entries if entry.button]
    if not include_params:
        entries = [entry for entry in entries if not entry.arg_hint]
    entries = entries[: MAX_ROWS * BUTTONS_PER_ROW]

    groups = (
        ([e for e in entries if not _is_long_label(e.command)], BUTTONS_PER_ROW),
        ([e for e in entries if _is_long_label(e.command)], LONG_BUTTONS_PER_ROW),
    )

    rows: list[Comp.ActionRow] = []
    for group, per_row in groups:
        for index in range(0, len(group), per_row):
            chunk = group[index : index + per_row]
            rows.append(
                Comp.ActionRow(
                    buttons=[_make_button(entry) for entry in chunk],
                    fallback_text=FALLBACK_TEXT,
                )
            )

    if len(rows) > MAX_ROWS:
        dropped = count_button_eligible(sections, include_params) - sum(
            len(row.buttons) for row in rows[:MAX_ROWS]
        )
        logger.warning(
            f"帮助按钮超出 QQ 键盘 {MAX_ROWS} 行上限，{dropped} 个指令未获按钮；"
            "正文应回退完整分节列表避免内容缺失"
        )
    return rows[:MAX_ROWS]
