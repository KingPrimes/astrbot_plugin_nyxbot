"""虚空商人卡片渲染器

从 CardRenderer 拆分出的 create_void_trader_card 独立实现。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image

from .draw_constant import ThemeColor
from .image_combiner import ImageCombiner

if TYPE_CHECKING:
    from ..model.world_state import VoidTrader
    from .card_renderer import CardRenderer


def render_void_trader_card(renderer: CardRenderer, trader: VoidTrader) -> Image.Image:
    """绘制虚空商人信息卡片。

    Args:
        renderer: CardRenderer 实例（提供字体等资源）。
        trader: VoidTrader 模型。
    """
    card_width = 800
    item_height = 55
    card_height = 80 + len(trader.manifest) * item_height + 20

    cb = ImageCombiner(card_width, max(card_height, 200), ThemeColor.BG_DARK)

    trader_name = trader.character or "Baro Ki'Teer"
    location = trader.node or "未知中继站"
    cb.set_color(ThemeColor.ACCENT_GOLD).set_font(renderer.font_title)
    cb.add_text(f"🏪 虚空商人 - {trader_name}", 25, 15)
    cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(renderer.font_small)
    cb.add_text(f"位置: {location}", 25, 42)

    eta = trader.time_left
    if eta:
        cb.set_color(ThemeColor.ACCENT).set_font(renderer.font_small)
        cb.add_text(f"剩余: {eta}", 640, 42)

    cb.draw_line(25, 68, 775, 68, width=2)

    y_offset = 82
    for i, m_item in enumerate(trader.manifest):
        bg_color = ThemeColor.BG_CARD if i % 2 == 0 else ThemeColor.BG_CARD_ALT
        cb.draw_rounded_rect(20, y_offset, 760, 45, radius=6, fill=bg_color)

        item_name = m_item.item or "未知物品"
        if "/" in str(item_name):
            item_name = str(item_name).split("/")[-1].replace("_", " ")
        ducats = m_item.prime_price or 0
        credits = m_item.regular_price or 0

        cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(renderer.font_body)
        cb.add_text(item_name, 35, y_offset + 8)
        cb.set_color(ThemeColor.ACCENT_GOLD).set_font(renderer.font_small)
        cb.add_text(f"{ducats}  ducats  |  {credits:,}  credits", 500, y_offset + 8)

        y_offset += item_height

    return cb.to_image()
