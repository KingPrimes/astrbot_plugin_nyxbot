"""钢铁之路卡片渲染器

从 CardRenderer 拆分出的 create_steel_path_card 独立实现。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image

from .draw_constant import ThemeColor
from .image_combiner import ImageCombiner

if TYPE_CHECKING:
    from ..model.world_state import SteelPathOffering
    from .card_renderer import CardRenderer


def render_steel_path_card(renderer: CardRenderer, steel_path: SteelPathOffering) -> Image.Image:
    """绘制钢铁之路卡片。

    Args:
        renderer: CardRenderer 实例（提供字体等资源）。
        steel_path: SteelPathOffering 模型。
    """
    card_width = 800
    essences = steel_path.evergreens
    item_height = 55
    card_height = 80 + len(essences) * item_height + 20

    cb = ImageCombiner(card_width, max(card_height, 180), ThemeColor.BG_DARK)

    cb.set_color(ThemeColor.ACCENT).set_font(renderer.font_title)
    cb.add_text("⚔ 钢铁之路", 25, 15)
    cb.draw_line(25, 48, 775, 48, width=2)

    rotation = steel_path.current_reward.name if steel_path.current_reward else ""
    if rotation:
        cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(renderer.font_body)
        cb.add_text(f"当前轮回: {rotation}", 35, 55)

    y_offset = 60 if not rotation else 85
    if essences:
        cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(renderer.font_small)
        cb.add_text("钢铁精华兑换:", 25, y_offset)
        y_offset += 25

        for i, e in enumerate(essences):
            bg_color = ThemeColor.BG_CARD if i % 2 == 0 else ThemeColor.BG_CARD_ALT
            cb.draw_rounded_rect(20, y_offset, 760, 45, radius=6, fill=bg_color)

            cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(renderer.font_body)
            cb.add_text(e.name, 35, y_offset + 8)
            cb.set_color(ThemeColor.ACCENT_GOLD).set_font(renderer.font_small)
            cb.add_text(f"{e.cost} 钢铁精华", 640, y_offset + 8)

            y_offset += item_height

    return cb.to_image()
