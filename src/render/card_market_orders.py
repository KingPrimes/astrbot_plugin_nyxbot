"""Market 订单卡片渲染器 — 迁移自 Java DefaultDrawMarketOrdersImage

布局：
  - 1550px 宽
  - 标题 + 平台/买卖切换按钮 + 杜卡币/交易税信息
  - 表格列: 价格 / 数量 / 等级 / 卖家 / 状态
  - 深色主题 + 看板娘立绘
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image

from .draw_constant import DrawConstant, ThemeColor
from .font_manager import FontManager
from .image_combiner import ImageCombiner
from .standing import draw_standing

if TYPE_CHECKING:
    from ..model.market import Orders
    from .card_renderer import CardRenderer

_CANVAS_W = 1550
_MARGIN = 40
_TITLE_H = 80
_HEADER_H = 50
_ROW_H = 55
_FOOTER_H = 40


def render_market_orders_card(
    renderer: CardRenderer,
    orders: Orders,
) -> Image.Image:
    """绘制 Market 订单卡片。

    Args:
        renderer: CardRenderer 实例。
        orders: Orders 模型。

    Returns:
        PIL Image 对象。
    """
    order_list = orders.orders
    if not order_list:
        return renderer.create_text_image(f"没有找到 {orders.name} 的订单数据", 800, 120)

    content_h = _HEADER_H + len(order_list) * _ROW_H
    canvas_h = _TITLE_H + content_h + _FOOTER_H + 200

    title_font = FontManager.get_text_font(36)
    info_font = FontManager.get_text_font(18)
    header_font = FontManager.get_text_font(18)
    row_font = FontManager.get_text_font(16)
    footer_font = FontManager.get_text_font(16)

    cb = ImageCombiner(_CANVAS_W, canvas_h, ThemeColor.BG_DARK)
    cb.draw_double_border(12, ThemeColor.TABLE_BORDER, ThemeColor.DIVIDER, 2)

    # --- 标题 ---
    current_y = 30
    cb.set_color(ThemeColor.ACCENT_GOLD).set_font(title_font)
    cb.add_centered_text(orders.name, current_y)
    current_y += 50

    # --- 分隔线 ---
    cb.set_color(ThemeColor.DIVIDER)
    cb.draw_line(_MARGIN + 20, current_y, _CANVAS_W - _MARGIN - 20, current_y, width=2)
    current_y += 20

    # --- 平台标签 ---
    plat_text = orders.form.upper() if orders.form else "PC"
    cb.set_color(ThemeColor.BG_CARD).set_font(info_font)
    cb.fill_rect(_MARGIN + 20, current_y - 10, 80, 36)
    cb.set_color(ThemeColor.TEXT_PRIMARY)
    cb.add_text(plat_text, _MARGIN + 42, current_y + 8)

    # --- 买卖标签 ---
    buy_color = ThemeColor.SUCCESS if not orders.is_by else ThemeColor.TEXT_MUTED
    sell_color = ThemeColor.SUCCESS if orders.is_by else ThemeColor.TEXT_MUTED
    cb.set_color(buy_color)
    cb.fill_rect(_MARGIN + 120, current_y - 10, 80, 36)
    cb.set_color(ThemeColor.TEXT_PRIMARY)
    cb.add_text("卖家", _MARGIN + 140, current_y + 8)
    cb.set_color(sell_color)
    cb.fill_rect(_MARGIN + 220, current_y - 10, 80, 36)
    cb.set_color(ThemeColor.TEXT_PRIMARY)
    cb.add_text("买家", _MARGIN + 240, current_y + 8)

    # --- 杜卡币 ---
    cb.set_color(ThemeColor.ACCENT_GOLD)
    cb.add_text("杜卡币:", _MARGIN + 350, current_y - 2)
    cb.add_text(str(orders.ducats), _MARGIN + 430, current_y + 14)

    # --- 交易税 ---
    cb.set_color(ThemeColor.ACCENT_BLUE)
    cb.add_text("交易税:", _MARGIN + 520, current_y - 2)
    cb.add_text(str(orders.trading_tax), _MARGIN + 600, current_y + 14)

    current_y += 40

    # --- 表头 ---
    cb.set_color(ThemeColor.DIVIDER)
    cb.draw_line(_MARGIN, current_y, _CANVAS_W - _MARGIN, current_y, width=1)
    current_y += 15

    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(header_font)
    header_items = [("价格", _MARGIN + 10), ("数量", _MARGIN + 150),
                    ("等级", _MARGIN + 350), ("卖家", _MARGIN + 550),
                    ("状态", _MARGIN + 950)]
    for text, x in header_items:
        cb.add_text(text, x, current_y + _HEADER_H // 2 + 6)

    current_y += _HEADER_H + 5

    # --- 数据行 ---
    for i, order in enumerate(order_list):
        if i % 2 == 1:
            cb.set_color(ThemeColor.BG_CARD_ALT)
            cb.fill_rect(_MARGIN, current_y + 2, _CANVAS_W - 2 * _MARGIN, _ROW_H - 4)

        platinum = str(order.platinum) if order.platinum is not None else "N/A"
        quantity = str(order.quantity) if order.quantity is not None else "N/A"
        rank = str(order.rank) if order.rank is not None else "-"
        seller = "未知"
        status = "未知"
        if order.user is not None:
            seller = order.user.ingame_name or "未知"
            status = order.user.status or "未知"

        cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(row_font)
        cb.add_text(platinum, _MARGIN + 10, current_y + _ROW_H // 2 + 6)
        cb.add_text(quantity, _MARGIN + 150, current_y + _ROW_H // 2 + 6)
        cb.add_text(rank, _MARGIN + 350, current_y + _ROW_H // 2 + 6)
        cb.add_text(seller, _MARGIN + 550, current_y + _ROW_H // 2 + 6)
        cb.add_text(status, _MARGIN + 950, current_y + _ROW_H // 2 + 6)

        current_y += _ROW_H

    # --- 看板娘 ---
    draw_standing(cb, max_w=310, max_h=420)

    # --- 底部署名 ---
    cb.set_color(ThemeColor.TEXT_MUTED).set_font(footer_font)
    cb.add_centered_text(DrawConstant.FOOTER_TEXT, canvas_h - _FOOTER_H)

    return cb.to_image()


def render_market_orders_possible_items_card(
    renderer: CardRenderer,
    possible_items: list[str],
) -> Image.Image:
    """绘制"可能要查询的物品列表"卡片。

    Args:
        renderer: CardRenderer 实例。
        possible_items: 物品名称列表。

    Returns:
        PIL Image 对象。
    """
    if not possible_items:
        return renderer.create_text_image("没有找到匹配的物品", 800, 120)

    content_h = len(possible_items) * _ROW_H
    canvas_h = _TITLE_H + content_h + _FOOTER_H + 150

    title_font = FontManager.get_text_font(28)
    header_font = FontManager.get_text_font(18)
    row_font = FontManager.get_text_font(16)
    footer_font = FontManager.get_text_font(16)

    cb = ImageCombiner(_CANVAS_W, canvas_h, ThemeColor.BG_DARK)
    cb.draw_double_border(12, ThemeColor.TABLE_BORDER, ThemeColor.DIVIDER, 2)

    current_y = _TITLE_H
    cb.set_color(ThemeColor.ACCENT_GOLD).set_font(title_font)
    cb.add_centered_text("可能要查询的物品列表", current_y)
    current_y += 50

    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(header_font)
    cb.add_text("序号", _MARGIN + 10, current_y + _HEADER_H // 2 + 8)
    cb.add_text("物品名称", _MARGIN + 150, current_y + _HEADER_H // 2 + 8)
    current_y += _HEADER_H + 5

    for idx, item in enumerate(possible_items, 1):
        if idx % 2 == 1:
            cb.set_color(ThemeColor.BG_CARD_ALT)
            cb.fill_rect(_MARGIN, current_y + 2, _CANVAS_W - 2 * _MARGIN, _ROW_H - 4)

        cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(row_font)
        cb.add_text(str(idx), _MARGIN + 20, current_y + _ROW_H // 2 + 8)
        cb.add_text(item, _MARGIN + 160, current_y + _ROW_H // 2 + 8)

        current_y += _ROW_H

    draw_standing(cb, max_w=310, max_h=420)
    cb.set_color(ThemeColor.TEXT_MUTED).set_font(footer_font)
    cb.add_centered_text(DrawConstant.FOOTER_TEXT, canvas_h - _FOOTER_H)

    return cb.to_image()
