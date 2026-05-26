"""午夜电波赛季信息卡片渲染器

采用 3 列卡片网格布局，镜像 Java DefaultDrawSeasonInfoImage.java：
  - 居中标题 + 赛季编号
  - 每张卡片: 类型标签(颜色编码) + 名称 + 描述(最多2行自动换行) + 声望
  - 双层边框 + 看板娘立绘(始终在最右侧) + 底部署名
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PIL import ImageFont

from .draw_constant import LayoutConstants, ThemeColor
from .font_manager import FontManager
from .image_combiner import ImageCombiner
from .standing import draw_standing_at
from .text_utils import wrap_text

if TYPE_CHECKING:
    from PIL import Image

    from ..model.world_state import SeasonInfo
    from .card_renderer import CardRenderer


# ---------------------------------------------------------------------------
# 布局常量
# ---------------------------------------------------------------------------

_CANVAS_W = 1800
_CONTENT_X, _CONTENT_W = LayoutConstants.get_content_bounds(_CANVAS_W)

_COLS = 3
_COL_GAP = 20
_CARD_W = (_CONTENT_W - (_COLS - 1) * _COL_GAP) // _COLS  # 546
_CARD_H = 240
_CARD_RADIUS = 14
_CARD_PAD = 20
_ROW_GAP = 16

_COL_X = (
    _CONTENT_X,                                            # Col 0: 60
    _CONTENT_X + _CARD_W + _COL_GAP,                       # Col 1: 626
    _CONTENT_X + 2 * (_CARD_W + _COL_GAP),                 # Col 2: 1192
)

_TITLE_Y = 60
_SEASON_Y = 126
_DIVIDER_Y = 160
_FOOTER_OFFSET = 50

# 类型颜色 (对齐 Java DailyDrawSeasonInfoImage)
_DAILY_COLOR: tuple[int, int, int] = (255, 149, 0)
_WEEKLY_COLOR: tuple[int, int, int] = (74, 144, 226)
_ELITE_COLOR: tuple[int, int, int] = (155, 89, 182)

# 看板娘
_STANDING_MAX_W = 360
_STANDING_MAX_H = 420

_SEASON_MIN_H = 600


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _build_type_label(
    challenge: SeasonInfo.ActiveChallenges,
) -> tuple[str, tuple[int, int, int]]:
    """构建类型标签文字和颜色，镜像 Java drawChallengeType()。"""
    parts: list[str] = []
    color: tuple[int, int, int] = ThemeColor.TEXT_SECONDARY

    if challenge.daily:
        parts.append("每日")
        color = _DAILY_COLOR
    if challenge.weekly:
        parts.append("每周")
        color = _WEEKLY_COLOR
    if challenge.elite:
        parts.append("精英")
        color = _ELITE_COLOR

    if not parts:
        parts.append("普通")
        color = ThemeColor.TEXT_SECONDARY

    return (" ".join(parts), color)


def _draw_one_challenge_card(
    cb: ImageCombiner,
    challenge: SeasonInfo.ActiveChallenges,
    card_x: int,
    card_y: int,
    type_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    name_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    desc_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    standing_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    desc_max_w: int,
) -> None:
    """绘制单张挑战任务卡片。"""
    inner_x = card_x + _CARD_PAD

    # 卡片背景
    cb.set_color(ThemeColor.BG_CARD)
    cb.draw_rounded_rect(card_x, card_y, _CARD_W, _CARD_H, radius=_CARD_RADIUS)

    # ---- 行 1: 类型标签 (30px) ----
    type_text, type_color = _build_type_label(challenge)
    cb.set_color(type_color).set_font(type_font)
    cb.add_text(type_text, inner_x, card_y + 34)

    # ---- 行 2: 任务名称 (30px) ----
    name = challenge.name or challenge.challenge or "未知任务"
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(name_font)
    cb.add_text(name, inner_x, card_y + 74)

    # ---- 行 3-4: 任务描述 (24px, 最多 2 行自动换行) ----
    description = challenge.description or ""
    if description:
        saved_font = cb.current_font
        cb.set_font(desc_font)
        desc_lines = wrap_text(cb.draw, description, desc_max_w, desc_font)
        cb.set_font(saved_font)
    else:
        desc_lines = []

    cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(desc_font)
    if not desc_lines:
        cb.add_text("无描述", inner_x, card_y + 112)
    elif len(desc_lines) == 1:
        cb.add_text(desc_lines[0], inner_x, card_y + 112)
    else:
        # 第 1 行
        cb.add_text(desc_lines[0], inner_x, card_y + 112)
        # 第 2 行（超过 2 行则截断末尾加 "..."）
        if len(desc_lines) > 2:
            line2 = desc_lines[1]
            max_chars = desc_max_w // 24 - 3  # 预留 "..." 空间
            line2 = line2[:max_chars] + "..."
        else:
            line2 = desc_lines[1]
        cb.add_text(line2, inner_x, card_y + 144)

    # ---- 行 5: 声望奖励 (24px, 金色) ----
    standing = challenge.standing or 0
    cb.set_color(ThemeColor.ACCENT_GOLD).set_font(standing_font)
    cb.add_text(f"声望: {standing}", inner_x, card_y + 184)


# ---------------------------------------------------------------------------
# 主渲染函数
# ---------------------------------------------------------------------------

def render_season_info_card(
    renderer: CardRenderer,
    season_info: SeasonInfo,
) -> Image.Image:
    """绘制午夜电波赛季信息卡片 — 3 列网格 + 双层边框 + 看板娘 + 底部署名。

    Args:
        renderer: CardRenderer 实例。
        season_info: SeasonInfo 模型。

    Returns:
        PIL Image 对象。
    """
    challenges = season_info.active_challenges
    if not challenges:
        return renderer.create_text_image("当前没有活跃的午夜电波挑战", 800, 120)

    # ---- 字体 ----
    title_font = FontManager.get_text_font(64)
    season_font = FontManager.get_text_font(32)
    type_font = FontManager.get_text_font(30)
    name_font = FontManager.get_text_font(30)
    desc_font = FontManager.get_text_font(24)
    standing_font = FontManager.get_text_font(24)
    FontManager.get_text_font(22)

    desc_max_w = _CARD_W - 2 * _CARD_PAD  # 506px

    # ---- 布局计算 ----
    n = len(challenges)
    rows = math.ceil(n / _COLS)
    last_row_full = n % _COLS == 0

    # 看板娘始终在 Col 2: 末行满则追加占位行
    if last_row_full:
        total_rows = rows + 1
        standing_card_row = rows  # 0-indexed: 新占位行
    else:
        total_rows = rows
        standing_card_row = rows - 1  # 末行 Col 2

    # ---- 内容起始 Y（用于高度计算） ----
    season = season_info.season
    divider_y = _SEASON_Y + 28 if season else _DIVIDER_Y
    content_start_y = divider_y + 36

    cards_h = total_rows * _CARD_H + (total_rows - 1) * _ROW_GAP
    content_end = content_start_y + cards_h
    canvas_h = max(content_end + _FOOTER_OFFSET + 30, _SEASON_MIN_H)

    # ---- 画布 ----
    cb = ImageCombiner(_CANVAS_W, canvas_h, ThemeColor.BG_DARK)

    # ---- 双层装饰边框 ----
    cb.draw_default_double_border()

    # ---- 标题 ----
    cb.set_color(ThemeColor.ACCENT_BLUE).set_font(title_font)
    cb.add_centered_text("午夜电波", _TITLE_Y)

    # 赛季编号
    if season:
        cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(season_font)
        cb.add_centered_text(f"第 {season} 季", _SEASON_Y)

    # ---- 分割线 ----
    cb.draw_content_divider(divider_y, _CONTENT_X, _CONTENT_W)

    # ---- 挑战卡片 (3 列网格) ----
    for i, challenge in enumerate(challenges):
        row = i // _COLS
        col = i % _COLS
        card_x = _COL_X[col]
        card_y = content_start_y + row * (_CARD_H + _ROW_GAP)
        _draw_one_challenge_card(
            cb, challenge, card_x, card_y,
            type_font, name_font, desc_font, standing_font, desc_max_w,
        )

    # ---- 看板娘 (始终在 Col 2) ----
    standing_x = _COL_X[2] + (_CARD_W - _STANDING_MAX_W) // 2
    standing_y = content_start_y + standing_card_row * (_CARD_H + _ROW_GAP)
    draw_standing_at(cb, standing_x, standing_y, _STANDING_MAX_W, _STANDING_MAX_H)

    # ---- 底部署名 ----
    cb.draw_card_footer(canvas_h, _FOOTER_OFFSET, 22)

    return cb.to_image()
