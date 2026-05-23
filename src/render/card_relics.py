"""遗物卡片渲染器

从 CardRenderer 拆分出的 create_relic_card 独立实现。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image

from .draw_constant import ThemeColor
from .image_combiner import ImageCombiner

if TYPE_CHECKING:
    from .card_renderer import CardRenderer


def render_relic_card(renderer: CardRenderer, relics: list[dict]) -> Image.Image:
    """绘制遗物信息卡片。

    Args:
        renderer: CardRenderer 实例（提供字体等资源）。
        relics: 遗物数据 dict 列表。
    """
    card_width = 800
    item_height = 50
    card_height = 60 + len(relics) * item_height + 20

    cb = ImageCombiner(card_width, max(card_height, 150), ThemeColor.BG_DARK)

    cb.set_color(ThemeColor.ACCENT_GOLD).set_font(renderer.font_title)
    cb.add_text("💎 当前遗物掉落", 25, 15)
    cb.draw_line(25, 48, 775, 48, width=2)

    y_offset = 65
    for i, relic in enumerate(relics):
        bg_color = ThemeColor.BG_CARD if i % 2 == 0 else ThemeColor.BG_CARD_ALT
        cb.draw_rounded_rect(20, y_offset, 760, 42, radius=6, fill=bg_color)

        name = relic.get("name", "未知遗物")
        tier = relic.get("tier", "")
        relics_name = relic.get("relic_name", "")

        display = f"{relics_name}" if relics_name else name
        if tier:
            display = f"{display} [{tier}]"

        cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(renderer.font_body)
        cb.add_text(display, 35, y_offset + 8)

        eta = relic.get("eta", "")
        if eta:
            cb.set_color(ThemeColor.ACCENT).set_font(renderer.font_small)
            cb.add_text(eta, 640, y_offset + 8)

        y_offset += item_height

    return cb.to_image()
