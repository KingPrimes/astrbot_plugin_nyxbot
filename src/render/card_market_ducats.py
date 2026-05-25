"""Market 杜卡币卡片渲染器 — 迁移自 Java DefaultDrawMarketDucatsImage

布局：
  - 1680px 宽，双列布局（当天 | 每小时）
  - 每列 5 个字段：名称 / 杜卡币 / 杜卡币/白金 / 均价 / 库存
  - 深色表头 + 斑马纹行 + 看板娘立绘
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image

from .draw_constant import DrawConstant, ThemeColor, lerp_color
from .font_manager import FontManager
from .image_combiner import ImageCombiner
from .standing import draw_standing

if TYPE_CHECKING:
    from ..model.market import DucatItem
    from .card_renderer import CardRenderer

_CANVAS_W = 1680
_MARGIN = 48
_COL_W = (_CANVAS_W - 3 * _MARGIN) // 2
_ROW_H = 60
_HEADER_H = 60
_TITLE_H = 96
_FOOTER_H = 48

# 列字段 X 偏移（相对于列起始 x）
_COL_NAME = 12
_COL_DUCATS = 264
_COL_DPP = 372
_COL_WA = 540
_COL_VOL = 648

# 排名渐变色终点
_RANK_END_COLOR = ThemeColor.TEXT_MUTED  # (120, 120, 120)


def _row_baseline(draw, row_y: int, row_h: int, font) -> int:
    """计算在行高内垂直居中的文本基线 Y 坐标。"""
    bbox = draw.textbbox((0, 0), "Ay", font=font)
    return int(row_y + row_h / 2 - (bbox[1] + bbox[3]) / 2)


def render_market_ducats_card(
    renderer: CardRenderer,
    day_items: list[DucatItem],
    hour_items: list[DucatItem],
    title: str,
) -> Image.Image:
    """绘制 Market 杜卡币卡片 — 镜像 Java drawMarketDucatsImage()。

    Args:
        renderer: CardRenderer 实例。
        day_items: 当天数据列表。
        hour_items: 每小时数据列表。
        title: 标题（"金垃圾" 或 "银垃圾"）。

    Returns:
        PIL Image 对象。
    """
    if not day_items and not hour_items:
        return renderer.create_text_image(f"当前没有{title}数据", 800, 120)

    max_rows = max(len(day_items), len(hour_items), 1)
    content_h = _HEADER_H * 2 + max_rows * _ROW_H
    canvas_h = _TITLE_H + content_h + _FOOTER_H + 120

    title_font = FontManager.get_text_font(58)
    subtitle_font = FontManager.get_text_font(26)
    header_font = FontManager.get_text_font(22)
    row_font = FontManager.get_text_font(20)
    footer_font = FontManager.get_text_font(22)

    cb = ImageCombiner(_CANVAS_W, canvas_h, ThemeColor.BG_DARK)
    cb.draw_double_border(12, ThemeColor.TABLE_BORDER, ThemeColor.DIVIDER, 2)

    # --- 标题 ---
    current_y = _TITLE_H
    cb.set_color(ThemeColor.ACCENT_GOLD).set_font(title_font)
    cb.add_centered_text(title, current_y - 68)

    left_x = _MARGIN
    right_x = _MARGIN + _COL_W + _MARGIN
    current_y += 30

    # --- 副标题行（当天 / 每小时）---
    cb.set_color(ThemeColor.BG_CARD)
    cb.fill_rect(left_x, current_y, _COL_W, _HEADER_H)
    cb.fill_rect(right_x, current_y, _COL_W, _HEADER_H)
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(subtitle_font)
    sub_baseline = _row_baseline(cb.draw, current_y, _HEADER_H, subtitle_font)
    sub_cx = _COL_W // 2
    cb.add_text("当天", left_x + sub_cx - cb.get_string_width("当天") // 2, sub_baseline)
    cb.add_text("每小时", right_x + sub_cx - cb.get_string_width("每小时") // 2, sub_baseline)

    current_y += _HEADER_H + 12

    # --- 表头行（字段名）---
    cb.set_color(ThemeColor.BG_CARD)
    cb.fill_rect(left_x, current_y, _COL_W, _HEADER_H)
    cb.fill_rect(right_x, current_y, _COL_W, _HEADER_H)
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(header_font)

    _draw_header(cb, left_x, current_y)
    _draw_header(cb, right_x, current_y)

    current_y += _HEADER_H + 6

    # 排名渐变色起点
    if "金" in title:
        rank_start_color = ThemeColor.ACCENT_GOLD  # (255, 215, 0)
    else:
        rank_start_color = (192, 192, 192)  # 亮银色

    # --- 数据行 ---
    for i in range(max_rows):
        if i < len(day_items):
            _draw_row(cb, day_items[i], left_x, current_y, i, max_rows, row_font, rank_start_color)
        else:
            _draw_empty_row(cb, left_x, current_y, i)

        if i < len(hour_items):
            _draw_row(cb, hour_items[i], right_x, current_y, i, max_rows, row_font, rank_start_color)
        else:
            _draw_empty_row(cb, right_x, current_y, i)

        current_y += _ROW_H

    # --- 看板娘 ---
    draw_standing(cb, max_w=190, max_h=260)

    # --- 底部署名 ---
    cb.set_color(ThemeColor.TEXT_MUTED).set_font(footer_font)
    cb.add_centered_text(DrawConstant.FOOTER_TEXT, canvas_h - _FOOTER_H)

    return cb.to_image()


def _draw_header(cb: ImageCombiner, x: int, y: int) -> None:
    """绘制单列表头字段。"""
    baseline_y = _row_baseline(cb.draw, y, _HEADER_H, cb.current_font)
    cb.add_text("名称", x + _COL_NAME, baseline_y)
    cb.add_text("杜卡币", x + _COL_DUCATS, baseline_y)
    cb.add_text("杜卡币/白金", x + _COL_DPP, baseline_y)
    cb.add_text("均价", x + _COL_WA, baseline_y)
    cb.add_text("库存", x + _COL_VOL, baseline_y)


def _draw_row(
    cb: ImageCombiner,
    item: DucatItem,
    x: int,
    y: int,
    idx: int,
    total: int,
    font,
    rank_start_color: tuple[int, int, int],
) -> None:
    """绘制单行数据，交替行背景色，排名渐变色。"""
    if idx % 2 == 1:
        cb.set_color(ThemeColor.BG_CARD_ALT)
        cb.fill_rect(x, y, _COL_W, _ROW_H)

    name = item.item_name or "未知物品"
    ducats_str = str(item.ducats) if item.ducats is not None else "N/A"
    dpp_str = f"{item.ducats_per_platinum_wa:.2f}" if item.ducats_per_platinum_wa is not None else "N/A"
    wa_str = f"{item.wa_price:.2f}" if item.wa_price is not None else "N/A"
    vol_str = str(item.volume) if item.volume is not None else "N/A"

    baseline_y = _row_baseline(cb.draw, y, _ROW_H, font)

    # 排名渐变色：整行统一
    t = idx / max(total - 1, 1)
    rank_color = lerp_color(rank_start_color, _RANK_END_COLOR, t)
    cb.set_color(rank_color).set_font(font)
    cb.add_text(name, x + _COL_NAME, baseline_y)
    cb.add_text(ducats_str, x + _COL_DUCATS, baseline_y)
    cb.add_text(dpp_str, x + _COL_DPP, baseline_y)
    cb.add_text(wa_str, x + _COL_WA, baseline_y)
    cb.add_text(vol_str, x + _COL_VOL, baseline_y)


def _draw_empty_row(cb: ImageCombiner, x: int, y: int, idx: int) -> None:
    """绘制空白行。"""
    if idx % 2 == 1:
        cb.set_color(ThemeColor.BG_CARD_ALT)
        cb.fill_rect(x, y, _COL_W, _ROW_H)
