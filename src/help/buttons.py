"""帮助消息的可点击按钮 / Interactive buttons for the help message

把帮助条目排成 QQ 内联键盘（AstrBot 的可移植 ``ActionRow``）：点一下按钮，
平台回传一个 ``ButtonInteraction``，由 ``src/commands/wf_help.py`` 里的
``button_action`` 处理器路由到对应指令。

按钮**默认只收可直接执行的指令**（无需参数，主色）——需要参数的指令由
``mqqapi`` 内联链接承载（点击自动把指令填入发送框，比按钮回提示更友好，
见 ``src/markdown/help.py``）；链接菜单关闭时传 ``include_params=True``，
参数指令以成功色按钮兜底（点击只回用法提示）。

**分页**：QQ 键盘上限 5 行，4 列布局下可读按钮位约 15 个，而插件指令
已超过这个数。因此按标签宽度切好的行会再按页切分——多页时每页留出
最后一行放「更多 ›」/「‹ 返回」导航按钮，保证条目不因容量上限而丢失
（早期实现直接截断，装不下的指令在默认形态下彻底不可见，2026-11-16
按用户反馈改为分页）。

约束（QQ 官方 / AstrBot 双侧，见 ``docs/qq-official-bot.md`` §7.3）：

- 单条消息最多 **5 行 × 每行 5 个**按钮；
- ``label`` 最多 **10 个字符**；
- 按钮 ``id`` 在同一条消息内必须**唯一**（AstrBot 会校验并抛错），
  因此每条指令的 id 都带指令名后缀，回调侧用前缀识别归属；
- 按钮只随 Markdown 消息发送——图片卡片路径不带按钮。

The keyboard is capped at 5x5 buttons with unique per-message ids; only the
Markdown delivery path carries it. Rows are split into pages when the entry
count exceeds one keyboard, with the last row of each multi-page keyboard
reserved for next/previous navigation.
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

#: 翻页按钮 id 前缀：``nyxbot:help:__page__:<页码>``（页码从 0 起）。
#: 与 ``HELP_BUTTON_PREFIX`` 同源前缀，回调侧先判翻页再判指令名。
HELP_PAGE_PREFIX = f"{HELP_BUTTON_PREFIX}__page__:"

#: 翻页按钮文案（label 上限 10 字符）。
PAGE_PREV_LABEL = "‹ 返回"
PAGE_NEXT_LABEL = "更多 ›"

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

#: 多页时每页留给指令的行数（最后一行放翻页导航）。
ROWS_PER_PAGE = MAX_ROWS - 1

#: 键盘不可用时的文字兜底（平台自身不支持按钮时由适配器使用）。
FALLBACK_TEXT = "当前平台不支持按钮，请直接发送上面的指令。"


def is_help_button(action_id: str) -> bool:
    """按钮回调是否属于帮助消息 / Whether the click came from a help button."""
    return action_id.startswith(HELP_BUTTON_PREFIX)


def is_help_page_button(action_id: str) -> bool:
    """是否帮助消息的翻页按钮 / Whether the click is a help page nav."""
    return action_id.startswith(HELP_PAGE_PREFIX)


def page_from_action_id(action_id: str) -> int | None:
    """从翻页按钮 id 取页码 / Parse the target page index.

    Returns:
        目标页下标（从 0 起）；id 格式非法或为负数时返回 ``None``。
    """
    raw = action_id.removeprefix(HELP_PAGE_PREFIX).strip()
    try:
        page = int(raw)
    except ValueError:
        return None
    return page if page >= 0 else None


def command_from_action_id(action_id: str) -> str:
    """从按钮 id 里取回指令名 / Extract the bare command from a button id."""
    return action_id.removeprefix(HELP_BUTTON_PREFIX).strip()


def _display_label(entry: HelpEntry) -> str:
    """按钮上显示的文字 / Label shown on the button.

    ``button_label`` 为允许长指令使用 2 字短名（如赏金三条显示「地球」），
    排版按它计算宽度，按钮回调仍用 ``command``。
    """
    return entry.button_label or entry.command


def _is_long_label(label: str) -> bool:
    """是否需要 2 列宽度的长标签按钮 / Whether the label needs a wide button.

    超过 2 个文字即视为长标签；纯数字按钮（如 ``1999``）不参与该规则。
    """
    return len(label) > LONG_LABEL_THRESHOLD and not label.isdigit()


def _make_button(entry: HelpEntry) -> Comp.Button:
    """按条目构建一个按钮 / Build one button for an entry.

    样式按能力区分：参数指令用成功色（仅 ``include_params`` 兜底模式
    会出现），无参数指令用主色。
    """
    return Comp.Button(
        id=f"{HELP_BUTTON_PREFIX}{entry.command}",
        label=_display_label(entry),
        action=Comp.Button.CallbackAction(data={"cmd": entry.command}),
        style=(
            Comp.Button.Style.SUCCESS
            if entry.arg_hint
            else Comp.Button.Style.PRIMARY
        ),
    )


def _make_page_button(page: int, label: str) -> Comp.Button:
    """构建一个翻页按钮 / Build one navigation button."""
    return Comp.Button(
        id=f"{HELP_PAGE_PREFIX}{page}",
        label=label,
        action=Comp.Button.CallbackAction(data={"page": page}),
        style=Comp.Button.Style.DEFAULT,
    )


def _make_row(entries: Sequence[HelpEntry]) -> Comp.ActionRow:
    """把一行条目装成 ``ActionRow`` / Wrap entries into one keyboard row."""
    return Comp.ActionRow(
        buttons=[_make_button(entry) for entry in entries],
        fallback_text=FALLBACK_TEXT,
    )


def count_button_eligible(
    sections: Sequence[HelpSection], include_params: bool = False
) -> int:
    """统计应进按钮的条目数 / Count entries eligible for a button slot.

    与 :func:`build_help_pages` 的筛选口径一致（``include_params`` 决定
    参数指令是否计入），供调用方判断分页是否完整覆盖了全部条目。
    """
    return sum(
        1
        for section in sections
        for entry in section.entries
        if entry.button and (include_params or not entry.arg_hint)
    )


def _layout_rows(entries: Sequence[HelpEntry]) -> list[list[HelpEntry]]:
    """按标签宽度分组切行 / Lay entries out into rows without a row cap.

    短标签（≤2 字 + 数字）一行 4 个、长标签一行 2 个；短组在前，
    保持目录顺序。不施加总行数上限——上限由 :func:`build_help_pages`
    按页处理。
    """
    groups = (
        ([entry for entry in entries if not _is_long_label(_display_label(entry))], BUTTONS_PER_ROW),
        ([entry for entry in entries if _is_long_label(_display_label(entry))], LONG_BUTTONS_PER_ROW),
    )
    rows: list[list[HelpEntry]] = []
    for group, per_row in groups:
        for index in range(0, len(group), per_row):
            rows.append(list(group[index : index + per_row]))
    return rows


def build_help_pages(
    sections: Sequence[HelpSection], include_params: bool = False
) -> list[list[Comp.ActionRow]]:
    """按帮助分节生成**分页**键盘 / Build paged inline keyboards.

    分两步：

    - **能力筛选**：默认只收可直接执行的指令（无需参数）——参数指令由
      ``mqqapi`` 内联链接承载（点击自动填入发送框）；``include_params=True``
      时（链接菜单关闭的兜底场景）参数指令也进按钮，点击只回用法提示。
    - **分页**：单页装得下（≤5 行）时不留导航行；超出时按每页 4 行切分，
      每页最后一行放「‹ 返回」/「更多 ›」，第一条/最后一条不显示对应方向。

    Args:
        sections: :func:`src.help.catalog.build_help_sections` 的返回值。
        include_params: 是否把需要参数的指令也排进按钮（兜底模式）。

    Returns:
        分页列表，每页是 ``ActionRow`` 列表；当前 AstrBot 不支持按钮
        （组件或回调装饰器任一缺失）时返回空列表，调用方退化为纯文本
        帮助——能力探测统一取自 ``src.util.framework_caps``，避免与
        ``registry`` 的回调注册探测不同步而发出死按钮。
    """
    if not BUTTONS_AVAILABLE:
        return []

    entries = [
        entry for section in sections for entry in section.entries if entry.button
    ]
    if not include_params:
        entries = [entry for entry in entries if not entry.arg_hint]
    if not entries:
        return []

    rows = _layout_rows(entries)
    if len(rows) <= MAX_ROWS:
        return [[_make_row(row) for row in rows]]

    # 均分而不是「前面塞满、最后一页剩一两行」：9 行 → 3/3/3，
    # 8 行 → 4/4，10 行 → 4/3/3
    page_count = -(-len(rows) // ROWS_PER_PAGE)
    base, extra = divmod(len(rows), page_count)
    chunks: list[list[list[HelpEntry]]] = []
    start = 0
    for index in range(page_count):
        size = base + (1 if index < extra else 0)
        chunks.append(rows[start : start + size])
        start += size

    pages: list[list[Comp.ActionRow]] = []
    for index, chunk in enumerate(chunks):
        page = [_make_row(row) for row in chunk]
        nav: list[Comp.Button] = []
        if index > 0:
            nav.append(_make_page_button(index - 1, PAGE_PREV_LABEL))
        if index < len(chunks) - 1:
            nav.append(_make_page_button(index + 1, PAGE_NEXT_LABEL))
        if nav:
            page.append(Comp.ActionRow(buttons=nav, fallback_text=FALLBACK_TEXT))
        pages.append(page)
    logger.debug(
        f"帮助按钮共 {len(entries)} 个、{len(rows)} 行，分 {len(pages)} 页（每页 ≤{ROWS_PER_PAGE} 行）"
    )
    return pages


def build_help_buttons(
    sections: Sequence[HelpSection], include_params: bool = False
) -> list[Comp.ActionRow]:
    """取第一页键盘 / Build the first keyboard page.

    保留此入口供调用方只需一页时使用；需要翻页时应改用
    :func:`build_help_pages`。
    """
    pages = build_help_pages(sections, include_params)
    return pages[0] if pages else []


def help_page_count(
    sections: Sequence[HelpSection], include_params: bool = False
) -> int:
    """键盘页数 / Number of keyboard pages (0 when buttons unavailable)."""
    return len(build_help_pages(sections, include_params))
