"""帮助 Markdown 文本格式化器 / Help Markdown Text Formatter

对应 ``card_help.py`` 的图片渲染：平台支持 Markdown 时直接发文本，
不支持时由命令侧降级为同一份内容的图片卡片。

三种排版（:func:`format_help_markdown` 的参数组合）：

- **链接菜单**（``link_menu=True``，默认开启）：正文是 ``mqqapi://aio/inlinecmd``
  内联指令链接列表——点击菜单项 QQ 客户端会把指令填入发送框（参数指令已带
  尾随空格），无需内联键盘权限；参考同类 QQ 机器人验证过的成熟做法；
- **精简版**（``compact=True``）：一句话 + ``***`` 分割线，分割线后只列需要
  参数的指令——无参数指令由按钮承载（链接菜单关闭而按钮可用时）；
- **完整版**：按分节列出全部指令，按钮 / 链接都不可用时的兜底，内容不缺。

排版约束（按 QQ 官方机器人的 Markdown 能力裁剪，
见 ``docs/qq-official-bot.md`` §7.2）：

- 只用 ``#`` / ``##`` 标题、``-`` 无序列表、``>`` 引用、``***`` 分割线与 ``**`` 加粗；
- 正文不放 ``http(s)`` 外链（需先在开放平台报备）；``mqqapi://`` 是客户端
  协议链接，与图片 URL 一样不经报备即可使用；
- 表格语法 2026-11-16 经 ``/表格测试`` 实测 QQ **已支持**（市场订单在用，
  见 ``src/markdown/market_orders.py``）；帮助正文的 ``➢`` 链接菜单
  形态不依赖表格，维持现状；
- 图片按 ``#宽px #高px`` 的**固定框**显示，比例不一致会被居中裁切——
  显示尺寸由配置 ``wf_help_logo_size`` 跟随图片比例调整；
- QQ 没有居中/对齐语法；默认用 256px 方形 logo 大尺寸展示，图占消息大半
  宽度后左对齐与否几乎不可辨，不再依赖居中横幅（需要时可自备横幅图）。

Layout is deliberately limited to headings, bullet lists, blockquotes, the
``***`` rule and bold (tables render fine on QQ since 2026-11 but the help
menu's link-list shape does not need them). Inline ``mqqapi://`` command
links (a proven client scheme used by peer bots) turn each menu item into a
tap-to-fill command; ``http(s)`` links stay out of the body since they
require platform pre-approval.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING
from urllib.parse import quote

from ..help.catalog import HELP_TITLE, HelpEntry, HelpSection

if TYPE_CHECKING:
    from collections.abc import Sequence

#: 顶部图标的默认显示尺寸（px，宽 x 高）。QQ 官方图片语法要求宽高带 ``px``
#: 单位：``![text #208px #320px](url)``。默认 ``256x256`` 对应仓库方形
#: ``logo.png``（512x512 二倍图，显示清晰）；大小不设上限（已实测）。
DEFAULT_LOGO_SIZE = (256, 256)

#: ``wf_help_logo_size`` 的合法格式：``宽x高``（1~4 位数字）。
_LOGO_SIZE_PATTERN = re.compile(r"^(\d{1,4})x(\d{1,4})$")

#: 链接菜单项文案：指令名 → (表情, 菜单标签)。
#: 缩写指令补上两字说明（WM→WM订单），让菜单无需注释即可读懂；
#: 未登记的指令回退为「▸ + 指令名」，新增条目不会因此缺行。
_MENU_LABELS: dict[str, tuple[str, str]] = {
    "平原": ("🌍", "平原"),
    "警报": ("🚨", "警报"),
    "突击": ("⚔️", "突击"),
    "裂隙": ("🌀", "虚空裂隙"),
    "钢铁裂隙": ("🛡️", "钢铁裂隙"),
    "九重天裂隙": ("🚀", "九重天裂隙"),
    "奸商": ("🤑", "奸商"),
    "钢铁": ("🗡️", "钢铁"),
    "仲裁": ("⚖️", "仲裁"),
    "仲裁表": ("📋", "仲裁表"),
    "1999": ("📅", "1999日历"),
    "WM": ("🛒", "WM订单"),
    "金垃圾": ("✨", "金垃圾"),
    "CD": ("👹", "CD玄骸"),
    "XT": ("🧬", "XT姐妹"),
    "WR": ("🎴", "WR紫卡"),
    "遗物": ("📦", "遗物"),
    "紫卡分析": ("🔍", "紫卡分析"),
}

#: 菜单里参数指令的提示行（按钮不在场时的完整菜单结尾）。
_MENU_HINT = "> 💡 带参数的指令点击后补上内容再发送即可"

#: 按钮在场时的菜单引言：无参数指令交给按钮，菜单只列参数指令。
_MENU_INTRO = "> 点击下方按钮直接查询；以下指令点击自动填入，补上参数发送即可"


def parse_logo_size(raw: str) -> tuple[int, int] | None:
    """解析「宽x高」尺寸配置 / Parse the configured ``WxH`` display size.

    Args:
        raw: 配置原文，如 ``256x256``；空白会自动去除。

    Returns:
        ``(宽, 高)``（至少 1px）；格式非法时返回 ``None``，调用方回退默认值。
    """
    match = _LOGO_SIZE_PATTERN.match((raw or "").strip())
    if match is None:
        return None
    return max(1, int(match.group(1))), max(1, int(match.group(2)))


def _entry_line(entry: HelpEntry) -> str:
    """一条指令帮助行 / One bullet line for an entry."""
    return f"- **{entry.usage}** — {entry.description}"


def _logo_lines(logo_url: str, logo_size: tuple[int, int]) -> list[str]:
    """顶部图标行 / Leading logo image line (empty when no URL configured)."""
    if not logo_url:
        return []
    width, height = logo_size
    # alt 固定用无空格短词，避免 QQ 宽松解析器对带空格 alt 的兼容问题
    return [f"![logo #{width}px #{height}px]({logo_url})", ""]


def _inline_command_url(command_text: str) -> str:
    """构造 ``mqqapi`` 内联指令链接 / Build an inline-command deep link.

    点击后 QQ 客户端把 ``command`` 填入发送框：``enter=false`` 表示不自动
    发送（用户确认后发出，与同类机器人行为一致）。
    """
    return (
        "mqqapi://aio/inlinecmd?command="
        f"{quote(command_text, safe='')}&enter=false&reply=true"
    )


def _menu_line(entry: HelpEntry) -> str:
    """一条可点击菜单项 / One clickable menu line."""
    emoji, label = _MENU_LABELS.get(entry.command, ("▸", entry.command))
    # 参数指令的链接带一个尾随空格（编码为 %20）：点击后输入框已就位，
    # 补上参数即可发送——与参考机器人「角色攻略查询」的做法相同。
    command_text = f"{entry.usage} " if entry.arg_hint else entry.usage
    return f"> ➢ [{emoji}{label}]({_inline_command_url(command_text)})"


def _menu_lines(
    sections: Sequence[HelpSection],
    logo_url: str,
    logo_size: tuple[int, int],
    params_only: bool = False,
) -> list[str]:
    """引用块内的链接菜单 / The tappable menu inside a blockquote.

    结构参考同类机器人的成熟排版：标题之后紧跟 ``> `` 引用块，图片与菜单
    行都在块内；条目按分节顺序输出，管理员运维指令与 ``wfhelp`` 不进菜单。

    ``params_only=True``（按钮在场时）：无参数指令由按钮直接查询，菜单只列
    需要参数的指令——``mqqapi`` 链接点击自动填入指令与空格，正是参数场景
    的最佳载体；``False``（按钮不可用）时菜单覆盖全部可查询指令。
    """
    lines: list[str] = []
    if logo_url:
        width, height = logo_size
        lines.append(f"> ![logo #{width}px #{height}px]({logo_url})")

    if params_only:
        lines.append(_MENU_INTRO)
        for section in sections:
            for entry in section.entries:
                if entry.button and entry.arg_hint:
                    lines.append(_menu_line(entry))
        return lines

    for section in sections:
        for entry in section.entries:
            if entry.button:
                lines.append(_menu_line(entry))
    lines.append(_MENU_HINT)
    return lines


def _compact_lines(sections: Sequence[HelpSection]) -> list[str]:
    """精简版正文：分割线后只列需要参数的指令 / Compact body: params only.

    无参数指令全部由按钮承载，正文不再介绍；管理员运维指令与
    ``wfhelp`` 也不做介绍（按钮能力由配色区分，见 ``src/help/buttons.py``）。
    """
    lines: list[str] = ["点击下方按钮直接查询对应数据", ""]

    listed: list[str] = []
    example: str | None = None
    for section in sections:
        for entry in section.entries:
            if not entry.arg_hint:
                continue
            listed.append(_entry_line(entry))
            if example is None and entry.arg_example:
                example = f"{entry.usage} {entry.arg_example}"

    if not listed:
        return lines

    # 官方文档：无序列表紧跟普通文本时必须空一行才能识别（标题后则不用）
    lines.extend(["***", "", "以下指令需要参数：", "", *listed])
    if example:
        lines.extend(["", f"> 参数跟在指令后即可，如 {example}"])

    return lines


def format_help_markdown(
    sections: Sequence[HelpSection],
    compact: bool = False,
    logo_url: str = "",
    logo_size: str = "",
    link_menu: bool = False,
    menu_params_only: bool = False,
) -> str:
    """把帮助分节格式化为 Markdown 文本 / Format help sections as Markdown.

    Args:
        sections: :func:`src.help.catalog.build_help_sections` 的返回值。
        compact: 精简模式（``link_menu=False`` 时生效）。按钮随消息发送时传
            ``True``——一句话 + 分割线 + 需要参数的指令；``False`` 为完整
            分节列表（按钮 / 链接都不可用时的兜底，内容不缺）。
        logo_url: 顶部图片的公网 URL（QQ 会下载转存）；空串表示不带图标。
        logo_size: 显示尺寸「宽x高」，需与图片比例一致（否则被居中裁切）；
            非法时回退 :data:`DEFAULT_LOGO_SIZE`（256x256，对应仓库 logo）。
        link_menu: 链接菜单模式。正文改为 ``mqqapi`` 内联指令链接列表，
            点击即把指令填入发送框；开启时 ``compact`` 被忽略。
        menu_params_only: 菜单只列需要参数的指令（按钮在场时）——无参数
            指令由按钮承载，正文不重复；``False`` 时菜单覆盖全部可查询
            指令（按钮不可用时的完整菜单）。

    Returns:
        可直接交给 ``event.plain_result()`` 的 Markdown 文本；
        空分节会被跳过，不会留下孤立的 ``##`` 标题。
    """
    size = parse_logo_size(logo_size) or DEFAULT_LOGO_SIZE

    if link_menu:
        # 参考同类机器人：标题后紧跟引用块（不留空行），图片与菜单都在块内
        lines: list[str] = [
            f"# {HELP_TITLE}",
            *_menu_lines(sections, logo_url, size, params_only=menu_params_only),
        ]
    else:
        lines = [*_logo_lines(logo_url, size), f"# {HELP_TITLE}", ""]
        if compact:
            lines.extend(_compact_lines(sections))
        else:
            for section in sections:
                if not section.entries:
                    continue
                lines.append(f"## {section.title}")
                lines.extend(_entry_line(entry) for entry in section.entries)
                lines.append("")

    # 去掉结尾多余空行（QQ 会把它计入消息长度，也是「格式正确」的一部分）
    while lines and not lines[-1]:
        lines.pop()

    return "\n".join(lines)
