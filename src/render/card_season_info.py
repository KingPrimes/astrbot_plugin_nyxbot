"""午夜电波赛季信息卡片渲染器

镜像 Java DefaultDrawSeasonInfoImage.java。
版式：页头（赛季编号作副标题）+ 3 列挑战卡片网格 + 看板娘 + 署名。

每张卡：类型标签（每日/每周/精英）→ 任务名 → 描述（最多 2 行）→ 声望。
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from . import card_frame as frame
from . import components as C
from .card_size import CardSpec, CustomBlock, measure_card_size
from .design import FONT, SPACE, font
from .theme import current_theme

if TYPE_CHECKING:
    from PIL import Image

    from ..model.world_state import SeasonInfo
    from .card_renderer import CardRenderer

#: 网格列数与卡片尺寸。
_COLUMNS = 3
_CARD_PAD = SPACE["lg"]
_CARD_MIN_W = 300


def _type_label(challenge, palette) -> tuple[str, tuple[int, int, int]]:
    """类型标签文字 + 颜色（对齐 Java drawChallengeType）。"""
    parts: list[str] = []
    color = palette.text_muted
    if challenge.daily:
        parts.append("每日")
        color = palette.amber
    if challenge.weekly:
        parts.append("每周")
        color = palette.blue
    if challenge.elite:
        parts.append("精英")
        color = palette.rarity_legendary
    if not parts:
        parts.append("普通")
    return " ".join(parts), color


def render_season_info_card(
    renderer: CardRenderer,
    season_info: SeasonInfo,
) -> Image.Image:
    """绘制午夜电波赛季信息卡片。

    Args:
        renderer: CardRenderer 实例（保留参数以兼容渲染入口）。
        season_info: SeasonInfo 模型。
    """
    challenges = season_info.active_challenges
    if not challenges:
        return renderer.create_text_image("当前没有活跃的午夜电波挑战", 800, 120)

    theme = current_theme()
    palette = theme.palette

    season = season_info.season
    subtitle = f"第 {season} 季" if season else ""

    gap = SPACE["lg"]
    grid_w = _CARD_MIN_W * _COLUMNS + gap * (_COLUMNS - 1)

    # 卡片高度只由字阶决定，与画布宽度无关 → 先定高度再看宽度
    line_h = FONT["sm"] + SPACE["xs"]
    card_h = (
        _CARD_PAD * 2
        + FONT["sm"] + SPACE["sm"]        # 类型标签
        + FONT["md"] + SPACE["sm"]        # 名称
        + 2 * line_h + SPACE["md"]        # 描述（固定预留 2 行，保证等高）
        + FONT["sm"]                      # 声望
    )

    rows = math.ceil(len(challenges) / _COLUMNS)
    grid_h = rows * card_h + max(0, rows - 1) * gap

    # 第一遍：拿到画布宽度，才能算卡片宽与描述换行宽度
    provisional = measure_card_size(
        CardSpec(
            title="午夜电波",
            subtitle=subtitle,
            blocks=[CustomBlock(width=grid_w, height=grid_h)],
            standing=None,
        )
    )
    content_w = provisional.content_width
    card_w = (content_w - gap * (_COLUMNS - 1)) // _COLUMNS
    desc_w = card_w - _CARD_PAD * 2

    # ---- 逐卡预排描述（换行宽度依赖卡片宽） ----
    prepared = []
    for challenge in challenges:
        name = challenge.name or challenge.challenge or "未知任务"
        type_text, type_color = _type_label(challenge, palette)
        desc_lines = C.wrap_lines(
            challenge.description or "无描述", desc_w, font("sm"), max_lines=2
        )
        prepared.append((type_text, type_color, name, desc_lines, challenge.standing or 0))

    # 末行有空位 → 看板娘塞进空位；否则走流式块
    slot_index = len(prepared)
    cell_standing = (
        frame.standing_cell_size(card_w, card_h * 2)
        if slot_index < rows * _COLUMNS
        else (0, 0)
    )
    extra_h = (
        max(0, cell_standing[1] - card_h) + SPACE["md"]
        if cell_standing[1]
        else frame.standing_block_height("md", content_w)
    )

    # 第二遍：把空位里立绘溢出的高度补进画布
    size = measure_card_size(
        CardSpec(
            title="午夜电波",
            subtitle=subtitle,
            blocks=[CustomBlock(width=grid_w, height=grid_h + extra_h)],
            standing=None,
        )
    )

    page = C.new_page(theme, size.width, size.height)
    y = C.draw_header(page, "午夜电波", subtitle)
    cb = page.cb

    for index, (type_text, type_color, name, desc_lines, standing) in enumerate(prepared):
        row, column = divmod(index, _COLUMNS)
        x = page.content_x + column * (card_w + gap)
        top = y + row * (card_h + gap)
        C.draw_grid_card(page, x, top, card_w, card_h)

        inner_x = x + _CARD_PAD
        cursor = top + _CARD_PAD

        cb.set_color(type_color).set_font(font("sm"))
        cb.add_text(C.fit_text(type_text, desc_w, font("sm")), inner_x, cursor)
        cursor += FONT["sm"] + SPACE["sm"]

        cb.set_color(palette.text).set_font(font("md", bold=True))
        cb.add_text(C.fit_text(name, desc_w, font("md", bold=True)), inner_x, cursor)
        cursor += FONT["md"] + SPACE["md"]

        cb.set_color(palette.text_muted).set_font(font("sm"))
        for line_index, line in enumerate(desc_lines):
            cb.add_text(line, inner_x, cursor + line_index * line_h)
        cursor += 2 * line_h + SPACE["md"]

        cb.set_color(palette.gold).set_font(font("sm"))
        cb.add_text(f"声望: {standing}", inner_x, cursor)

    if cell_standing[1]:
        slot_row, slot_col = divmod(slot_index, _COLUMNS)
        cell_x = page.content_x + slot_col * (card_w + gap)
        cell_y = y + slot_row * (card_h + gap)
        frame.draw_standing_in_cell(page, cell_x, cell_y, card_w, card_h * 2)
    else:
        frame.draw_standing_block(page, y + grid_h, "md")

    frame.draw_footer_block(page)
    return page.cb.to_image()
