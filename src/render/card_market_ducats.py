"""Market 杜卡币卡片渲染器 — 迁移自 Java DefaultDrawMarketDucatsImage

布局：
  - 1400px 宽，双列布局（当天 | 每小时）
  - 每列 5 个字段：名称 / 杜卡币 / 杜卡币/白金 / 均价 / 库存
  - 深色表头 + 斑马纹行 + 看板娘立绘
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image

from .draw_constant import DrawConstant, ThemeColor
from .font_manager import FontManager
from .image_combiner import ImageCombiner
from .standing import draw_standing

if TYPE_CHECKING:
    from ..model.market import DucatItem
    from .card_renderer import CardRenderer

_CANVAS_W = 1400
_MARGIN = 40
_COL_W = (_CANVAS_W - 3 * _MARGIN) // 2
_ROW_H = 50
_HEADER_H = 50
_TITLE_H = 60
_FOOTER_H = 40


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
    canvas_h = _TITLE_H + content_h + _FOOTER_H + 100

    title_font = FontManager.get_text_font(28)
    header_font = FontManager.get_text_font(18)
    row_font = FontManager.get_text_font(16)
    footer_font = FontManager.get_text_font(18)

    cb = ImageCombiner(_CANVAS_W, canvas_h, ThemeColor.BG_DARK)
    cb.draw_double_border(12, ThemeColor.TABLE_BORDER, ThemeColor.DIVIDER, 2)

    # --- 标题 ---
    current_y = _TITLE_H
    cb.set_color(ThemeColor.ACCENT_GOLD).set_font(title_font)
    cb.add_centered_text(title, current_y)

    left_x = _MARGIN
    right_x = _MARGIN + _COL_W + _MARGIN
    current_y += 30

    # --- 副标题行（当天 / 每小时）---
    cb.set_color(ThemeColor.BG_CARD)
    cb.fill_rect(left_x, current_y, _COL_W, _HEADER_H)
    cb.fill_rect(right_x, current_y, _COL_W, _HEADER_H)
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(header_font)
    cb.add_text("当天", left_x + _COL_W // 2 - 16, current_y + _HEADER_H // 2 + 6)
    cb.add_text("每小时", right_x + _COL_W // 2 - 24, current_y + _HEADER_H // 2 + 6)

    current_y += _HEADER_H + 10

    # --- 表头行（字段名）---
    cb.set_color(ThemeColor.BG_CARD)
    cb.fill_rect(left_x, current_y, _COL_W, _HEADER_H)
    cb.fill_rect(right_x, current_y, _COL_W, _HEADER_H)
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(header_font)

    _draw_header(cb, left_x, current_y)
    _draw_header(cb, right_x, current_y)

    current_y += _HEADER_H + 5

    # --- 数据行 ---
    for i in range(max_rows):
        if i < len(day_items):
            _draw_row(cb, day_items[i], left_x, current_y, i, row_font)
        else:
            _draw_empty_row(cb, left_x, current_y, i)

        if i < len(hour_items):
            _draw_row(cb, hour_items[i], right_x, current_y, i, row_font)
        else:
            _draw_empty_row(cb, right_x, current_y, i)

        current_y += _ROW_H

    # --- 看板娘 ---
    draw_standing(cb, max_w=310, max_h=420)

    # --- 底部署名 ---
    cb.set_color(ThemeColor.TEXT_MUTED).set_font(footer_font)
    cb.add_centered_text(DrawConstant.FOOTER_TEXT, canvas_h - _FOOTER_H)

    return cb.to_image()


def _draw_header(cb: ImageCombiner, x: int, y: int) -> None:
    """绘制单列表头字段。"""
    cb.add_text("名称", x + 10, y + _HEADER_H // 2 + 6)
    cb.add_text("杜卡币", x + 250, y + _HEADER_H // 2 + 6)
    cb.add_text("杜卡币/白金", x + 350, y + _HEADER_H // 2 + 6)
    cb.add_text("均价", x + 500, y + _HEADER_H // 2 + 6)
    cb.add_text("库存", x + 600, y + _HEADER_H // 2 + 6)


def _draw_row(cb: ImageCombiner, item: DucatItem, x: int, y: int, idx: int, font) -> None:
    """绘制单行数据，交替行背景色。"""
    if idx % 2 == 1:
        cb.set_color(ThemeColor.BG_CARD_ALT)
        cb.fill_rect(x, y, _COL_W, _ROW_H)

    name = item.item_name or "未知物品"
    if len(name) > 12:
        name = name[:9] + "..."

    ducats_str = str(item.ducats) if item.ducats is not None else "N/A"
    dpp_str = f"{item.ducats_per_platinum_wa:.2f}" if item.ducats_per_platinum_wa is not None else "N/A"
    wa_str = f"{item.wa_price:.2f}" if item.wa_price is not None else "N/A"
    vol_str = str(item.volume) if item.volume is not None else "N/A"

    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(font)
    cb.add_text(name, x + 10, y + _ROW_H // 2 + 6)
    cb.add_text(ducats_str, x + 250, y + _ROW_H // 2 + 6)
    cb.add_text(dpp_str, x + 350, y + _ROW_H // 2 + 6)
    cb.add_text(wa_str, x + 500, y + _ROW_H // 2 + 6)
    cb.add_text(vol_str, x + 600, y + _ROW_H // 2 + 6)


def _draw_empty_row(cb: ImageCombiner, x: int, y: int, idx: int) -> None:
    """绘制空白行。"""
    if idx % 2 == 1:
        cb.set_color(ThemeColor.BG_CARD_ALT)
        cb.fill_rect(x, y, _COL_W, _ROW_H)
