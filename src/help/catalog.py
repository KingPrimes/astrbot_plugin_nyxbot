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


#: 帮助正文：``(分节标题, (条目, ...))``。
#: 指令名不带前缀，前缀由 :func:`build_help_sections` 统一拼接。
#: 顺序与旧版 ``/wfhelp`` 文本一致，仅按主题分组，**不增删任何条目**。
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
            _EntrySpec("奸商", "查看虚空商人"),
            _EntrySpec("钢铁", "查看钢铁之路"),
            _EntrySpec("仲裁", "查看仲裁任务"),
            _EntrySpec("仲裁表", "查看有价值的未来仲裁"),
            # 管理员运维指令：会重拉全量数据，不放进按钮，避免误触
            _EntrySpec("更新仲裁", "重拉仲裁时间表（管理员）", button=False),
            _EntrySpec("更新分级", "重拉仲裁节点分级（管理员）", button=False),
            _EntrySpec("1999", "查看1999日历"),
        ),
    ),
    (
        "市场行情",
        (
            _EntrySpec("WM", "查询Warframe.Market订单", "物品名称", "膛线"),
            _EntrySpec("金垃圾", "查看杜卡德金币"),
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
