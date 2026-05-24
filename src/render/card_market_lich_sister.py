"""Market 赤毒/信条卡片渲染器 — 迁移自 Java DefaultDrawMarketLichSisterImage

布局：
  - 1350px 宽
  - 标题（物品名称 + 拍卖信息）
  - 表格列: 元素 / 伤害 / 起拍价 / 买断价 / 卖家 / 声望
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
    from ..model.market import MarketLichSister
    from .card_renderer import CardRenderer

_CANVAS_W = 1350
_MARGIN = 40
_TITLE_H = 60
_HEADER_H = 50
_ROW_H = 60
_FOOTER_H = 40

# 元素颜色映射 — 对应 Java ElementEnum
_ELEMENT_COLORS: dict[str, tuple[int, int, int]] = {
    "electricity": (149, 90, 185),
    "impact": (146, 149, 149),
    "radiation": (158, 148, 12),
    "magnetic": (80, 87, 94),
    "cold": (44, 83, 181),
    "toxin": (79, 130, 47),
    "heat": (229, 110, 12),
}

_ELEMENT_NAMES: dict[str, str] = {
    "electricity": "电击",
    "impact": "冲击",
    "radiation": "辐射",
    "magnetic": "磁力",
    "cold": "冰冻",
    "toxin": "毒素",
    "heat": "火焰",
}


def render_market_lich_sister_card(
    renderer: CardRenderer,
    data: MarketLichSister,
    title_suffix: str,
) -> Image.Image:
    """绘制 Market 赤毒/信条拍卖卡片。

    Args:
        renderer: CardRenderer 实例。
        data: MarketLichSister 模型。
        title_suffix: 标题后缀（"赤毒" 或 "信条"）。

    Returns:
        PIL Image 对象。
    """
    pay = data.payload
    if pay is None or not pay.auctions:
        return renderer.create_text_image(f"当前没有{title_suffix}拍卖数据", 800, 120)

    item_name = pay.item_name or "未知武器"
    auctions = pay.auctions
    content_h = _HEADER_H + len(auctions) * _ROW_H
    canvas_h = _TITLE_H + content_h + _FOOTER_H + 100

    title_font = FontManager.get_text_font(26)
    header_font = FontManager.get_text_font(18)
    row_font = FontManager.get_text_font(16)
    footer_font = FontManager.get_text_font(16)

    cb = ImageCombiner(_CANVAS_W, canvas_h, ThemeColor.BG_DARK)
    cb.draw_double_border(12, ThemeColor.TABLE_BORDER, ThemeColor.DIVIDER, 2)

    current_y = _TITLE_H
    cb.set_color(ThemeColor.ACCENT_GOLD).set_font(title_font)
    cb.add_centered_text(f"{item_name} {title_suffix}拍卖信息", current_y)
    current_y += 30

    # --- 表头 ---
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(header_font)
    cb.add_text("元素", _MARGIN + 10, current_y + _HEADER_H // 2 + 8)
    cb.add_text("伤害", _MARGIN + 200, current_y + _HEADER_H // 2 + 8)
    cb.add_text("起拍价", _MARGIN + 300, current_y + _HEADER_H // 2 + 8)
    cb.add_text("买断价", _MARGIN + 400, current_y + _HEADER_H // 2 + 8)
    cb.add_text("卖家", _MARGIN + 650, current_y + _HEADER_H // 2 + 8)
    cb.add_text("声望", _MARGIN + 1000, current_y + _HEADER_H // 2 + 8)
    current_y += _HEADER_H + 5

    # --- 数据行 ---
    for i, auction in enumerate(auctions):
        if i % 2 == 1:
            cb.set_color(ThemeColor.BG_CARD_ALT)
            cb.fill_rect(_MARGIN, current_y + 2, _CANVAS_W - 2 * _MARGIN, _ROW_H - 4)

        item = auction.item
        element_key = item.element if item else None
        element_name = _ELEMENT_NAMES.get(element_key or "", element_key or "未知")
        element_color = _ELEMENT_COLORS.get(element_key or "", ThemeColor.TEXT_SECONDARY)
        damage = str(item.damage) if item and item.damage is not None else "未知"
        starting = str(auction.starting_price) if auction.starting_price is not None else "无"
        buyout = str(auction.buyout_price) if auction.buyout_price is not None else "无"
        seller = "未知"
        reputation = "未知"
        if auction.owner is not None:
            seller = auction.owner.ingame_name or "未知"
            reputation = str(auction.owner.reputation) if auction.owner.reputation is not None else "未知"

        cb.set_color(element_color).set_font(row_font)
        cb.add_text(element_name, _MARGIN + 10, current_y + _ROW_H // 2 + 8)
        cb.set_color(ThemeColor.TEXT_PRIMARY)
        cb.add_text(damage, _MARGIN + 210, current_y + _ROW_H // 2 + 8)
        cb.add_text(starting, _MARGIN + 320, current_y + _ROW_H // 2 + 8)
        cb.add_text(buyout, _MARGIN + 420, current_y + _ROW_H // 2 + 8)
        cb.add_text(seller, _MARGIN + 550, current_y + _ROW_H // 2 + 8)
        cb.add_text(reputation, _MARGIN + 1010, current_y + _ROW_H // 2 + 8)

        current_y += _ROW_H

    draw_standing(cb, max_w=310, max_h=420)
    cb.set_color(ThemeColor.TEXT_MUTED).set_font(footer_font)
    cb.add_centered_text(DrawConstant.FOOTER_TEXT, canvas_h - _FOOTER_H)

    return cb.to_image()
