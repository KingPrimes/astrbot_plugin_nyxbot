"""帮助内容目录 / Help content catalog

帮助内容的**唯一来源**：Markdown 文本（``src/markdown/help.py``）、图片卡片
（``src/render/card_help.py``）与可点击按钮（``src/help/buttons.py``）都由这里的
同一份结构化数据生成，因此「多种发送方式内容完全一致」由结构保证，
而不是靠几处手写同步。

The single source of truth for help content. Markdown text, the image card and
the interactive buttons are all generated from this module.

每条指令额外声明了三件与「按钮」有关的信息 / Per-entry button metadata:

- ``command``：不带前缀的指令名，同时用作按钮 id 与回调数据；
- ``arg_hint``：需要参数时填参数说明，按钮被点击时只回用法提示，不再触发指令；
- ``button``：是否出现在按钮行里（管理员运维指令、帮助本身不占按钮位）。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HelpEntry:
    """一条指令帮助 / One command entry.

    ``usage`` 已包含指令前缀（如 ``/wf 平原`` 或 ``/平原``），
    展示时直接使用，不再各自拼接。
    """

    #: 不带前缀的指令名，按钮 id / 回调数据都用它（如 ``平原``）。
    command: str
    usage: str
    description: str
    #: 需要参数时的参数说明；``None`` 表示该指令无需参数，可直接按钮触发。
    arg_hint: str | None = None
    #: 参数示例（拼在 ``usage`` 后面），``None`` 表示不给示例。
    arg_example: str | None = None
    #: 是否在帮助消息里附带按钮。
    button: bool = True
    #: 按钮上显示的文字；``None`` 表示直接用 ``command``。
    #: 只影响显示宽度（QQ 键盘按 2 字/列排版），按钮回调仍用 ``command``。
    button_label: str | None = None


@dataclass(frozen=True)
class HelpSection:
    """一组指令帮助 / A titled group of command entries."""

    title: str
    entries: tuple[HelpEntry, ...]


@dataclass(frozen=True)
class _EntrySpec:
    """``_SECTIONS`` 的静态描述（前缀与 usage 在构建时才拼）。"""

    command: str
    description: str
    arg_hint: str | None = None
    arg_example: str | None = None
    button: bool = True
    button_label: str | None = None


#: 帮助正文：``(分节标题, (条目, ...))``。
#: 指令名不带前缀，前缀由 :func:`build_help_sections` 统一拼接。
#: 条目必须与 ``src/commands`` 里注册的指令一一对应（测试按 AST 校验），
#: 新增指令时同步补这里，否则帮助里看不到；``button=False`` 只用于
#: 管理员运维指令与帮助自身（不占键盘位）。
#:
#: 刻意不列的两条（测试白名单里有登记）：
#: - ``/w``：市场卡片配套的取句快捷指令，**只随卡片提示出现**——图片版在
#:   表格下方印「回复 /w 序号」，Markdown 版直接把序号做成按钮，用户不需要
#:   从帮助里学它（2026-11-16 用户要求）；
#: - ``/RM``：紫卡市场功能尚未实现（stub），列出来只会让人点了空欢喜。
_SECTIONS: tuple[tuple[str, tuple[_EntrySpec, ...]], ...] = (
    (
        "世界状态",
        (
            _EntrySpec("平原", "查看平原周期"),
            _EntrySpec("警报", "查看当前警报"),
            _EntrySpec("突击", "查看每日突击"),
            # 裂隙共三种（wf_fissures 注册的三个指令），帮助此前漏列两种
            _EntrySpec("裂隙", "查看虚空裂隙"),
            _EntrySpec("钢铁裂隙", "查看钢铁之路裂隙"),
            _EntrySpec("九重天裂隙", "查看虚空风暴（九重天）"),
            _EntrySpec("入侵", "查看当前入侵"),
            _EntrySpec("奸商", "查看虚空商人"),
            _EntrySpec("钢铁", "查看钢铁之路"),
            _EntrySpec("仲裁", "查看仲裁任务"),
            _EntrySpec("仲裁表", "查看有价值的未来仲裁"),
            _EntrySpec("执刑官猎杀", "查看本周执刑官猎杀（Archon Hunt）"),
            _EntrySpec("1999", "查看1999日历"),
            _EntrySpec("每日特惠", "查看达尔沃每日特惠"),
            _EntrySpec("轮换", "查看双衍王境周期"),
            _EntrySpec("电波", "查看午夜电波"),
        ),
    ),
    (
        "赏金任务",
        (
            # 三条都是长标签（>2 字），QQ 键盘长标签一行只放 2 个，
            # 因此排在第二个键盘页；正文不给参数提示，直接点按钮即可
            _EntrySpec("希图斯", "查看希图斯（地球）赏金"),
            _EntrySpec("英择谛", "查看英择谛（火卫二）赏金"),
            _EntrySpec("索拉里斯", "查看索拉里斯（金星）赏金"),
        ),
    ),
    (
        "市场行情",
        (
            _EntrySpec("WM", "查询Warframe.Market订单", "物品名称", "膛线"),
            _EntrySpec("金垃圾", "查看杜卡德金币"),
            _EntrySpec("银垃圾", "查看杜卡德银币"),
            _EntrySpec("CD", "查询赤毒巫妖拍卖", "武器名称", "布拉玛"),
            _EntrySpec("XT", "查询信条姐妹拍卖", "武器名称", "循环"),
            _EntrySpec("WR", "查询紫卡拍卖", "武器名称", "绝路"),
        ),
    ),
    (
        "数据与工具",
        (
            _EntrySpec("遗物", "查询遗物数据", "遗物名或奖励名", "中纪 A1"),
            _EntrySpec(
                "紫卡分析",
                "OCR识别紫卡",
                "紫卡截图（发指令后 30 秒内上传，或图文一起发送）",
            ),
            # 帮助本身不需要按钮
            _EntrySpec("wfhelp", "显示本帮助", button=False),
        ),
    ),
    (
        "管理员",
        (
            # 会重拉全量数据，不放进按钮，避免误触
            _EntrySpec("更新仲裁", "重拉仲裁时间表（管理员）", button=False),
            _EntrySpec("更新分级", "重拉仲裁节点分级（管理员）", button=False),
        ),
    ),
)

#: 帮助卡片 / Markdown 的标题。
HELP_TITLE = "NyxBot Warframe 助手"

#: 卡片页头副标题（Markdown 版不渲染副标题，分节标题已足够分层）。
HELP_SUBTITLE = "指令帮助"


def command_usage(command: str, prefix: str = "") -> str:
    """把指令名拼成可直接发送的形式 / Build a runnable command string.

    Args:
        command: 不带前缀的指令名（如 ``平原``）。
        prefix: ``wf_command_prefix`` 的值；为空表示无指令组前缀。

    Returns:
        ``"/wf 平原"``（有前缀）或 ``"/平原"``（无前缀），与 ``registry.py``
        的注册方式一致。
    """
    return f"/{prefix} {command}" if prefix else f"/{command}"


def build_help_sections(prefix: str = "") -> tuple[HelpSection, ...]:
    """按当前指令前缀生成帮助分节 / Build help sections for the given prefix.

    Args:
        prefix: ``wf_command_prefix`` 的值，通常直接取 ``registry.command_prefix``。

    Returns:
        不可变的分节元组，可直接交给 Markdown 格式化器、卡片渲染器或按钮构建器。
    """
    return tuple(
        HelpSection(
            title=title,
            entries=tuple(
                HelpEntry(
                    command=spec.command,
                    usage=command_usage(spec.command, prefix),
                    description=spec.description,
                    arg_hint=spec.arg_hint,
                    arg_example=spec.arg_example,
                    button=spec.button,
                    button_label=spec.button_label,
                )
                for spec in specs
            ),
        )
        for title, specs in _SECTIONS
    )


def find_help_entry(
    command: str, sections: tuple[HelpSection, ...] | None = None
) -> HelpEntry | None:
    """按指令名查帮助条目 / Look up one entry by bare command name.

    Args:
        command: 不带前缀的指令名，来自按钮回调数据。
        sections: 预构建的分节；``None`` 时按无前缀重建（仅供查询元信息）。

    Returns:
        命中的条目，未登记时返回 ``None``（旧按钮 / 目录已改）。
    """
    pool = sections if sections is not None else build_help_sections()
    for section in pool:
        for entry in section.entries:
            if entry.command == command:
                return entry
    return None
