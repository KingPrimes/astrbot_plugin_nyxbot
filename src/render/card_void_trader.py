"""虚空商人卡片渲染器 — 迁移自 Java DefaultDrawVoidTraderImage

采用表格式布局：
  - 居中标题 + 双层装饰边框
  - 商人位置 + 剩余时间
  - 商品清单表格（表头 + 数据行）
  - 杜卡币/星币图标 + 价格
  - 看板娘立绘 + 底部署名
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import ImageFont

from ..wenum.icon import IconEnum
from .draw_constant import DrawConstant, ThemeColor
from .font_manager import FontManager
from .image_combiner import ImageCombiner
from .standing import draw_standing

if TYPE_CHECKING:
    from PIL import Image

    from ..model.world_state import VoidTrader


# ---------------------------------------------------------------------------
# 布局常量
# ---------------------------------------------------------------------------

_CANVAS_W = 1400
_MARGIN = 40
_CONTENT_PAD = 20
_CONTENT_X = _MARGIN + _CONTENT_PAD
_CONTENT_W = _CANVAS_W - 2 * _CONTENT_X

# 表格列宽 — 镜像 Java columnWidths = {600, 200, 200}，按比例适配 1400px 画布
_COL_ITEM_W = 700
_COL_DUCATS_W = 250
_COL_CREDITS_W = 250

_TABLE_HEADER_H = 60
_ROW_H = 45

_MIN_HEIGHT = 800

_TITLE_Y = 70
_DIVIDER_Y = 138
_TRADER_INFO_Y = 160
_TABLE_START_Y = 230
_REGION_GAP = 30                      # 区域间距

_FOOTER_OFFSET = 55

_STANDING_MAX_W = 310
_STANDING_MAX_H = 420

# 颜色常量
_HEADER_BG_COLOR = (44, 62, 80)       # #2C3E50
_ITEM_NAME_COLOR = (52, 152, 219)     # #3498DB
_LOCATION_COLOR = (155, 89, 182)      # #9B59B6
_DUCATS_COLOR = (156, 129, 64)        # #9c8140
_CREDITS_COLOR = (69, 119, 143)       # #45778f


# ---------------------------------------------------------------------------
# 主渲染函数
# ---------------------------------------------------------------------------

def render_void_trader_card(
    trader: VoidTrader,
) -> Image.Image:
    """绘制虚空商人信息卡片 — 镜像 Java DefaultDrawVoidTraderImage.drawVoidTraderImage()。

    Args:
        renderer: CardRenderer 实例。
        trader: VoidTrader 模型。

    Returns:
        PIL Image 对象。
    """
    manifest = trader.manifest if trader.manifest else []
    item_count = len(manifest)

    # ---- 动态高度计算 ----
    content_h = (_TABLE_START_Y
                 + _TABLE_HEADER_H
                 + item_count * _ROW_H
                 + _REGION_GAP
                 + _STANDING_MAX_H
                 + _FOOTER_OFFSET)
    canvas_h = max(content_h, _MIN_HEIGHT)

    # ---- 字体 ----
    title_font = FontManager.get_text_font(46)
    info_font = FontManager.get_text_font(28)
    table_header_font = FontManager.get_text_font(26)
    table_row_font = FontManager.get_text_font(24)
    icon_font = FontManager.get_wf_icon_font(28)
    footer_font = FontManager.get_text_font(20)

    # ---- 画布 ----
    cb = ImageCombiner(_CANVAS_W, canvas_h, ThemeColor.BG_DARK)

    # ---- 双层边框 ----
    cb.draw_double_border(
        border_padding=16,
        border_color_outer=ThemeColor.TABLE_BORDER,
        border_color_inner=ThemeColor.DIVIDER,
        stroke=3,
    )

    # ---- 标题 ----
    trader_name = trader.character or "Baro Ki'Teer"
    cb.set_color(ThemeColor.ACCENT_BLUE).set_font(title_font)
    cb.add_centered_text(f"虚空商人 - {trader_name}", _TITLE_Y)

    # ---- 分割线 ----
    cb.set_color(ThemeColor.DIVIDER)
    cb.draw_line(_CONTENT_X, _DIVIDER_Y, _CONTENT_X + _CONTENT_W, _DIVIDER_Y, width=1)

    # ---- 商人信息行 ----
    _draw_trader_info(cb, trader, info_font)

    # ---- 商品表格 ----
    _draw_manifest_table(cb, manifest, table_header_font, table_row_font, icon_font)

    # ---- 看板娘 ----
    draw_standing(cb, max_w=_STANDING_MAX_W, max_h=_STANDING_MAX_H)

    # ---- 底部署名 ----
    cb.set_color(ThemeColor.TEXT_MUTED).set_font(footer_font)
    cb.add_centered_text(DrawConstant.FOOTER_TEXT, canvas_h - _FOOTER_OFFSET)

    return cb.to_image()


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _draw_trader_info(
    cb: ImageCombiner,
    trader: VoidTrader,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """绘制商人基本信息行（位置 + 剩余时间）。

    镜像 Java drawTraderInfo():
      - 位置: 紫色
      - 剩余时间: 文本色
    """
    # 位置
    location = trader.node or "未知位置"
    cb.set_color(_LOCATION_COLOR).set_font(font)
    cb.add_text(f"位置: {location}", _CONTENT_X + 200, _TRADER_INFO_Y)

    # 剩余时间
    time_left = trader.time_left or "未知"
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(font)
    cb.add_text(f"剩余时间: {time_left}", _CONTENT_X + 750, _TRADER_INFO_Y)


def _draw_manifest_table(
    cb: ImageCombiner,
    manifest: list,
    header_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    row_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    icon_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """绘制商品清单表格。

    镜像 Java drawManifestTable():
      - 表头深色背景 + 白色文字
      - 三列：物品名称 | 杜卡币价格 | 星币价格
    """
    table_x = _CONTENT_X
    table_w = _CONTENT_W

    col_widths = [_COL_ITEM_W, _COL_DUCATS_W, _COL_CREDITS_W]
    headers = ["物品名称", "杜卡币价格", "星币价格"]

    # ---- 表头背景 ----
    cb.set_color(_HEADER_BG_COLOR)
    cb.fill_rect(table_x, _TABLE_START_Y, table_w, _TABLE_HEADER_H)

    # ---- 表头文字 ----
    cb.set_color((255, 255, 255)).set_font(header_font)
    header_x = table_x
    for i, header_text in enumerate(headers):
        cb.add_text(header_text, header_x + 20, _TABLE_START_Y + _TABLE_HEADER_H // 2 - 4)
        header_x += col_widths[i]

    # ---- 数据行 ----
    current_y = _TABLE_START_Y + _TABLE_HEADER_H
    for item in manifest:
        _draw_manifest_row(cb, item, current_y, table_x, col_widths, row_font, icon_font)
        current_y += _ROW_H


def _draw_manifest_row(
    cb: ImageCombiner,
    item,
    row_y: int,
    start_x: int,
    col_widths: list[int],
    row_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    icon_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """绘制单个商品行。

    镜像 Java drawManifestRow():
      - 物品名称（蓝色）
      - 杜卡币图标 + 价格
      - 星币图标 + 价格（格式化: credits/1000 + "K"）
    """
    text_y = row_y + _ROW_H // 2 - 4

    # 列 1: 物品名称
    item_name = item.item or "未知物品"
    # 清理路径格式的物品名称 — 取最后一段
    if "/" in str(item_name):
        item_name = str(item_name).split("/")[-1].replace("_", " ")
    cb.set_color(_ITEM_NAME_COLOR).set_font(row_font)
    cb.add_text(item_name, start_x + 20, text_y)

    # 列 2: 杜卡币价格（图标 + 数值）
    ducats_price = str(item.prime_price) if item.prime_price is not None else "0"
    cb.set_color(_DUCATS_COLOR).set_font(icon_font)
    cb.add_text(IconEnum.DUCATS.icon, start_x + col_widths[0] + 20, text_y)
    cb.set_color(_DUCATS_COLOR).set_font(row_font)
    cb.add_text(ducats_price, start_x + col_widths[0] + 60, text_y)

    # 列 3: 星币价格（图标 + 格式化数值）
    regular_price = item.regular_price or 0
    credits_text = f"{regular_price / 1000:.0f}K" if regular_price >= 1000 else str(regular_price)
    cb.set_color(_CREDITS_COLOR).set_font(icon_font)
    cb.add_text(IconEnum.CREDITS.icon, start_x + col_widths[0] + col_widths[1] + 20, text_y)
    cb.set_color(_CREDITS_COLOR).set_font(row_font)
    cb.add_text(credits_text, start_x + col_widths[0] + col_widths[1] + 60, text_y)
