"""紫卡分析卡片渲染器 — 3 列网格布局

仿 card_market_riven.py 的暗色主题 + 圆角卡片 + 看板娘装饰。
每卡内容：武器名 / 紫卡后缀 / 倾向点 / 倾向数值 / 武器类型 / 词条列表。
diff 含 "-" 时红色 (172, 24, 24)、否则绿色 (59, 154, 33)，
与 Java DefaultDrawRivenAnalyseTrendImage 一致。
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PIL import Image, ImageFont

from .draw_constant import DrawConstant, ThemeColor
from .font_manager import FontManager
from .image_combiner import ImageCombiner
from .standing import draw_standing_at

if TYPE_CHECKING:
    from ..service.riven_analyse import RivenAnalyseResult
    from .card_renderer import CardRenderer


# ---------------------------------------------------------------------------
# Layout constants / 布局常量
# ---------------------------------------------------------------------------

_CANVAS_W = 1950
_MARGIN = 52
_CONTENT_PAD = 26
_CONTENT_X = _MARGIN + _CONTENT_PAD  # 78
_CONTENT_W = _CANVAS_W - 2 * _CONTENT_X  # 1794

_COLS = 3
_COL_GAP = 32
_CARD_W = (_CONTENT_W - _COL_GAP * (_COLS - 1)) // _COLS  # 576
_CARD_H = 480
_CARD_RADIUS = 20
_CARD_PAD = 26
_ROW_GAP = 26

_TITLE_Y = 90
_FOOTER_OFFSET = 72

# 看板娘
_STANDING_INROW_W, _STANDING_INROW_H = 420, 520
_STANDING_BELOW_W, _STANDING_BELOW_H = 340, 494

_CONTENT_START_Y = 170

# 卡片内布局 / Per-card y offsets
_CARD_HEADER_END = 107
_CARD_META_Y = 127
_CARD_META_LINE_H = 32
_CARD_ATTR_START = 210
_CARD_ATTR_ROW_H = 52

# 差异颜色（与 Java 一致）
_DIFF_UP = (59, 154, 33)       # 正向差异 → 绿色
_DIFF_DOWN = (172, 24, 24)      # 负向差异 → 红色

_RIVEN_SUFFIX_COLOR = (134, 105, 167)  # 紫卡后缀色


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _truncate(cb: ImageCombiner, text: str, max_w: int) -> str:
    if cb.get_string_width(text) <= max_w:
        return text
    ellipsis = "…"
    while text and cb.get_string_width(text + ellipsis) > max_w:
        text = text[:-1]
    return text + ellipsis if text else ellipsis


def _format_float(v: float) -> str:
    """格式化数值：保留必要的小数位，去掉末尾多余的零。"""
    return f"{v:.1f}" if v == int(v) else f"{v:.4g}"


# ---------------------------------------------------------------------------
# 单卡片绘制
# ---------------------------------------------------------------------------

def _draw_analyse_card(
    cb: ImageCombiner,
    result: RivenAnalyseResult,
    card_x: int,
    card_y: int,
    fonts: dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont],
) -> None:
    inner_x = card_x + _CARD_PAD
    inner_right = card_x + _CARD_W - _CARD_PAD
    inner_w = inner_right - inner_x

    # 卡片背景 + 边框
    cb.draw_rounded_rect(
        card_x, card_y, _CARD_W, _CARD_H,
        radius=_CARD_RADIUS,
        fill=ThemeColor.BG_CARD,
        outline=ThemeColor.TABLE_BORDER,
        stroke_width=1,
    )

    # 武器名（金色）
    cb.set_color(ThemeColor.ACCENT_GOLD).set_font(fonts["weapon"])
    cb.add_text(_truncate(cb, result.weapon_name, inner_w), inner_x, card_y + 23)

    # 紫卡后缀
    if result.riven_name:
        cb.set_color(_RIVEN_SUFFIX_COLOR).set_font(fonts["suffix"])
        cb.add_text(
            _truncate(cb, f"紫卡: {result.riven_name}", inner_w),
            inner_x, card_y + 65,
        )

    # 分隔线
    cb.set_color(ThemeColor.DIVIDER)
    cb.draw_line(
        inner_x, card_y + _CARD_HEADER_END,
        inner_right, card_y + _CARD_HEADER_END,
        width=1,
    )

    # 倾向信息：倾向点 (左) + 倾向数值 (右) 同行，武器类型下一行
    meta_y = card_y + _CARD_META_Y
    cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(fonts["meta"])
    cb.add_text(f"倾向点: {result.dot}", inner_x, meta_y)
    omega_text = f"倾向数值: {result.omega:.2f}"
    cb.add_text(omega_text, inner_right - cb.get_string_width(omega_text), meta_y)
    cb.add_text(
        f"武器类型: {result.weapon_type}",
        inner_x, meta_y + _CARD_META_LINE_H,
    )

    # 词条
    if not result.attributes:
        return

    # 分隔线
    cb.set_color(ThemeColor.DIVIDER)
    cb.draw_line(
        inner_x, card_y + _CARD_ATTR_START - 12,
        inner_right, card_y + _CARD_ATTR_START - 12,
        width=1,
    )

    attr_y = card_y + _CARD_ATTR_START
    attrs = result.attributes
    for i, attr in enumerate(attrs):
        color = _DIFF_DOWN if "-" in attr.diff else _DIFF_UP

        # 左列：词条名（垂直居中）
        cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(fonts["attr"])
        cb.add_text(attr.attribute_name, inner_x, attr_y + 6)

        # 右列上行：(low% - high%) 右对齐
        range_text = f"({_format_float(attr.low)}% - {_format_float(attr.high)}%)"
        cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(fonts["attr_small"])
        cb.add_text(range_text, inner_right - cb.get_string_width(range_text), attr_y)

        # 右列下行：| diff 右对齐，红/绿色
        cb.set_color(color).set_font(fonts["attr_val"])
        diff_text = f"| {attr.diff}"
        cb.add_text(diff_text, inner_right - cb.get_string_width(diff_text), attr_y + 26)

        attr_y += _CARD_ATTR_ROW_H + 8

        # 词条间分隔线（最后一条不加）
        if i < len(attrs) - 1:
            cb.set_color(ThemeColor.DIVIDER)
            cb.draw_line(
                inner_x, attr_y - 2,
                inner_right, attr_y - 2,
                width=1,
            )


# ---------------------------------------------------------------------------
# 主渲染函数
# ---------------------------------------------------------------------------

def render_riven_analyse_card(
    renderer: CardRenderer,
    results: list[RivenAnalyseResult],
) -> Image.Image:
    """绘制紫卡分析卡片 — 3 列圆角网格。

    Args:
        renderer: CardRenderer 实例。
        results: 紫卡分析结果列表（每把候选武器一张卡片）。

    Returns:
        PIL Image 对象。
    """
    if not results:
        return renderer.create_text_image("未识别到紫卡信息", 1040, 156)

    n = len(results)
    rows = math.ceil(n / _COLS)
    cards_h = rows * _CARD_H + (rows - 1) * _ROW_GAP
    last_row_count = n - (rows - 1) * _COLS
    last_row_y = _CONTENT_START_Y + (rows - 1) * (_CARD_H + _ROW_GAP)
    standing_in_row = last_row_count < _COLS

    content_end = _CONTENT_START_Y + cards_h
    if standing_in_row:
        canvas_h = max(
            content_end,
            last_row_y + _STANDING_INROW_H + _FOOTER_OFFSET + 12,
        )
    else:
        canvas_h = content_end + _STANDING_BELOW_H + _FOOTER_OFFSET + 26

    # 字体
    title_font = FontManager.get_text_font(60)
    footer_font = FontManager.get_text_font(24)

    fonts: dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont] = {
        "weapon": FontManager.get_text_font(26),
        "suffix": FontManager.get_text_font(22),
        "meta": FontManager.get_text_font(20),
        "attr": FontManager.get_text_font(22),
        "attr_small": FontManager.get_text_font(20),
        "attr_val": FontManager.get_text_font(22),
    }

    cb = ImageCombiner(_CANVAS_W, canvas_h, ThemeColor.BG_DARK)
    cb.draw_double_border(
        border_padding=20,
        border_color_outer=ThemeColor.TABLE_BORDER,
        border_color_inner=ThemeColor.DIVIDER,
        stroke=3,
    )

    # 标题
    cb.set_color(ThemeColor.ACCENT_GOLD).set_font(title_font)
    cb.add_centered_text("紫卡分析趋势", _TITLE_Y)

    # 卡片网格
    col_xs = [_CONTENT_X + i * (_CARD_W + _COL_GAP) for i in range(_COLS)]
    for i, res in enumerate(results):
        row = i // _COLS
        col = i % _COLS
        card_x = col_xs[col]
        card_y = _CONTENT_START_Y + row * (_CARD_H + _ROW_GAP)
        _draw_analyse_card(cb, res, card_x, card_y, fonts)

    # 看板娘
    if standing_in_row:
        rightmost_col = _COLS - 1
        standing_x = col_xs[rightmost_col] + (_CARD_W - _STANDING_INROW_W) // 2
        draw_standing_at(
            cb, standing_x, last_row_y,
            _STANDING_INROW_W, _STANDING_INROW_H,
        )
    else:
        standing_x = _CONTENT_X + _CONTENT_W - _STANDING_BELOW_W - 26
        draw_standing_at(
            cb, standing_x, content_end + 12,
            _STANDING_BELOW_W, _STANDING_BELOW_H,
        )

    # Footer
    cb.set_color(ThemeColor.TEXT_MUTED).set_font(footer_font)
    cb.add_centered_text(DrawConstant.FOOTER_TEXT, canvas_h - _FOOTER_OFFSET)

    return cb.to_image()
