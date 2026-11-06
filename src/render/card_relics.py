"""遗物卡片渲染器

版式：页头（``遗物查询``）+ 三列遗物卡 + 看板娘 + 署名。

每张卡：遗物名（金色居中）+ 奖励清单（按铜 → 银 → 金 → 紫排序，稀有度着色）。
卡片宽 = 最长一行（夹在 340~520），高 = 名称行 + 奖励行数累加，整张卡统一取最高的一张，
这样三列网格不会出现高低不齐。

看板娘占一个「虚拟格位」：末行没排满就落在空位里，排满了就另起一行的第一格，
两种情况下都只向下溢出，不会压到卡片。
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import card_frame as frame
from . import components as C
from .card_size import CardSpec, CustomBlock, measure_card_size
from .design import FONT, MAX_WIDTH, PAD, RGB, SPACE, font
from .theme import current_theme

if TYPE_CHECKING:
    from PIL import Image

    from ..model.export.relics import Relics
    from .card_renderer import CardRenderer

#: 每行列数。
_COLUMNS = 3
#: 列间距 / 行间距。
_GAP = SPACE["lg"]
#: 卡片内边距。
_CARD_PAD = SPACE["lg"]
#: 卡片宽下限 / 上限。
_MIN_CARD_W = 340
_MAX_CARD_W = 520
#: 单条奖励行高。
_REWARD_LINE_H = FONT["base"] + SPACE["xs"]


@dataclass(frozen=True)
class _RelicCard:
    """一张遗物卡的绘制文案。"""

    name: str
    rewards: list[tuple[str, RGB]]
    height: int


def _rarity_color(rarity: str | None, palette) -> RGB:
    """稀有度 → 主题色板（未知名按常见处理）。"""
    return {
        0: palette.rarity_common,
        1: palette.rarity_uncommon,
        2: palette.rarity_rare,
        3: palette.rarity_legendary,
    }[C.rarity_rank(rarity)]


def _build_card(relic: Relics, palette) -> _RelicCard:
    """把一个遗物转成绘制文案。"""
    name = relic.name or relic.uniqueName or "未知遗物"
    rewards = sorted(
        relic.relic_rewards,
        key=lambda reward: (C.rarity_rank(reward.rarity), reward.rewardName or ""),
    )
    lines = [
        (reward.get_reward_name(), _rarity_color(reward.rarity, palette)) for reward in rewards
    ]
    height = _CARD_PAD * 2 + FONT["lg"] + SPACE["md"] + len(lines) * _REWARD_LINE_H
    return _RelicCard(name=name, rewards=lines, height=height)


def _center_text(page, text: str, text_font, color: RGB, x: int, width: int, y: int) -> None:
    """在 ``[x, x+width)`` 内水平居中绘制一行。"""
    shown = C.fit_text(text, width, text_font)
    page.cb.set_color(color).set_font(text_font)
    page.cb.add_text(shown, x + (width - C.measure(shown, text_font)) // 2, y)


def _draw_card(page, card: _RelicCard, x: int, y: int, width: int, height: int) -> None:
    """画一张遗物卡（名称居中 + 奖励逐行居中）。"""
    palette = page.palette
    C.draw_grid_card(page, x, y, width, height)

    inner_w = width - _CARD_PAD * 2
    name_font = font("lg", bold=True)
    _center_text(
        page, card.name, name_font, palette.gold, x + _CARD_PAD, inner_w, y + _CARD_PAD
    )

    cursor_y = y + _CARD_PAD + FONT["lg"] + SPACE["md"]
    reward_font = font("base")
    for text, color in card.rewards:
        _center_text(page, text, reward_font, color, x + _CARD_PAD, inner_w, cursor_y)
        cursor_y += _REWARD_LINE_H


def render_relic_card(
    renderer: CardRenderer,
    relics: list[Relics],
) -> Image.Image:
    """绘制遗物信息卡片。

    Args:
        renderer: CardRenderer 实例（保留参数以兼容渲染入口）。
        relics: Relics 模型列表（已 prefetch ``relic_rewards``）。

    Returns:
        PIL Image 对象。
    """
    if not relics:
        return renderer.create_text_image("未找到遗物数据", 800, 120)

    theme = current_theme()
    palette = theme.palette
    cards = [_build_card(relic, palette) for relic in relics]
    subtitle = f"共 {len(cards)} 个遗物"

    # ---- 卡片尺寸：宽取最长一行，高取最高的一张（网格才齐）----
    name_font = font("lg", bold=True)
    reward_font = font("base")
    intrinsic = 0
    for card in cards:
        intrinsic = max(intrinsic, C.measure(card.name, name_font))
        for text, _color in card.rewards:
            intrinsic = max(intrinsic, C.measure(text, reward_font))
    # 三列布局时单卡不能超过「内容宽 ÷ 3」，否则最后一列会被画布裁掉
    max_card_w = (MAX_WIDTH - PAD * 2 - (_COLUMNS - 1) * _GAP) // _COLUMNS
    card_w = max(_MIN_CARD_W, min(_MAX_CARD_W, max_card_w, intrinsic + _CARD_PAD * 2))
    card_h = max(card.height for card in cards)

    # ---- 看板娘占一个虚拟格位 ----
    slot_w = card_w - _CARD_PAD * 2
    cell = frame.standing_cell_size(slot_w, card_h * 2)
    reserved = 1 if cell[1] else 0
    extra_h = max(0, cell[1] - card_h) if cell[1] else 0

    total_slots = len(cards) + reserved
    grid_rows = math.ceil(total_slots / _COLUMNS)
    grid_w = card_w * _COLUMNS + (_COLUMNS - 1) * _GAP
    grid_h = grid_rows * card_h + (grid_rows - 1) * _GAP

    size = measure_card_size(
        CardSpec(
            title="遗物查询",
            subtitle=subtitle,
            blocks=[CustomBlock(width=grid_w, height=grid_h + extra_h)],
            standing=None,
        )
    )

    page = C.new_page(theme, size.width, size.height)
    y = C.draw_header(page, "遗物查询", subtitle)

    grid_x = page.content_x + max(0, (page.content_w - grid_w) // 2)
    for index, card in enumerate(cards):
        row, column = divmod(index, _COLUMNS)
        _draw_card(page, card, grid_x + column * (card_w + _GAP), y + row * (card_h + _GAP), card_w, card_h)

    if reserved:
        row, column = divmod(len(cards), _COLUMNS)
        frame.draw_standing_in_cell(
            page,
            grid_x + column * (card_w + _GAP) + _CARD_PAD,
            y + row * (card_h + _GAP),
            slot_w,
            card_h * 2,
        )
    frame.draw_footer_block(page)
    return page.cb.to_image()


# ---------------------------------------------------------------------------
# 使用说明卡（/遗物 无参数时展示）
# ---------------------------------------------------------------------------

#: 用法条目：(标签, 示例指令, 说明)。
_HELP_ROWS: tuple[tuple[str, str, str], ...] = (
    ("按遗物名", "/遗物 中纪 A1", "精确查这一个遗物，只出 1 张卡"),
    ("按奖励", "/遗物 Frost Prime", "列出含该奖励的所有遗物（如 13 条）"),
    ("按拼音", "/遗物 zhongji", "与 /遗物 中纪 等价，支持全拼/首字母"),
    ("按别名", "/核桃 后纪 S5", "/核桃 是 /遗物 的别名，用法相同"),
)

#: 只写档位时的提示。
_HELP_TIERS = "古纪 / 前纪 / 中纪 / 后纪 / 安魂"


def render_relic_help_card(renderer: CardRenderer) -> Image.Image:
    """绘制 `/遗物` 使用说明卡片：四条用法 + 「只写档位会被拒绝」提示。

    Args:
        renderer: CardRenderer 实例（保留参数以兼容渲染入口）。

    Returns:
        PIL Image 对象。
    """
    theme = current_theme()
    palette = theme.palette

    label_font = font("sm")
    cmd_font = font("md")
    desc_font = font("base")
    label_w = max(C.measure(label, label_font) for label, _cmd, _desc in _HELP_ROWS)
    body_x = _CARD_PAD + label_w + SPACE["3xl"]
    body_w = max(
        max(C.measure(cmd, cmd_font), C.measure(desc, desc_font))
        for _label, cmd, desc in _HELP_ROWS
    )

    row_h = FONT["md"] + SPACE["xs"] + FONT["base"] + SPACE["lg"]
    warn_h = FONT["sm"] + SPACE["sm"] + FONT["base"] + SPACE["md"] * 2
    warn_title = "只写档位会被拒绝"
    warn_text = f"{_HELP_TIERS} 只是档位，请补上编号（如 中纪 A1）"
    panel_w = max(
        body_x + body_w + _CARD_PAD,
        _CARD_PAD * 2 + C.measure(warn_title, label_font) + SPACE["3xl"] + C.measure(warn_text, desc_font),
    )
    panel_h = (
        _CARD_PAD * 2
        + len(_HELP_ROWS) * (row_h + SPACE["sm"])
        + warn_h
    )

    size = measure_card_size(
        CardSpec(
            title="遗物查询使用说明",
            blocks=[CustomBlock(width=panel_w, height=panel_h)],
            standing="md",
            header_gap=SPACE["md"],
        )
    )

    page = C.new_page(theme, size.width, size.height)
    y = C.draw_header(page, "遗物查询使用说明")

    top = y + SPACE["md"]
    row_w = max(panel_w, page.content_w)
    cursor_y = top + _CARD_PAD

    for label, command, desc in _HELP_ROWS:
        C.draw_grid_card(page, page.content_x, cursor_y, row_w, row_h)
        page.cb.set_color(palette.gold).set_font(label_font)
        page.cb.add_text(
            label, page.content_x + _CARD_PAD, cursor_y + (row_h - FONT["sm"]) // 2
        )
        page.cb.set_color(palette.text).set_font(cmd_font)
        page.cb.add_text(command, page.content_x + body_x, cursor_y + SPACE["sm"])
        page.cb.set_color(palette.text_muted).set_font(desc_font)
        page.cb.add_text(
            desc,
            page.content_x + body_x,
            cursor_y + SPACE["sm"] + FONT["md"] + SPACE["xs"],
        )
        cursor_y += row_h + SPACE["sm"]

    # 警示：只写档位会被拒绝
    C.draw_grid_card(page, page.content_x, cursor_y, row_w, warn_h)
    page.cb.set_color(palette.amber).set_font(label_font)
    page.cb.add_text(warn_title, page.content_x + _CARD_PAD, cursor_y + SPACE["md"])
    page.cb.set_color(palette.text_muted).set_font(desc_font)
    page.cb.add_text(
        warn_text,
        page.content_x + _CARD_PAD,
        cursor_y + SPACE["md"] + FONT["sm"] + SPACE["sm"],
    )

    frame.draw_standing_block(page, top + panel_h, "md")
    frame.draw_footer_block(page)
    return page.cb.to_image()
