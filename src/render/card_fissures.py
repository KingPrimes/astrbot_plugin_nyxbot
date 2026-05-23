"""裂隙卡片渲染器

从 CardRenderer 拆分出的 create_fissure_card 独立实现。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image

from .draw_constant import ThemeColor
from .image_combiner import ImageCombiner

if TYPE_CHECKING:
    from .card_renderer import CardRenderer


def render_fissure_card(renderer: CardRenderer, fissures: list[dict]) -> Image.Image:
    """绘制裂隙信息卡片。

    Args:
        renderer: CardRenderer 实例（提供字体等资源）。
        fissures: 裂隙数据 dict 列表。
    """
    card_width = 800
    item_height = 80
    card_height = 60 + len(fissures) * item_height + 20

    cb = ImageCombiner(card_width, max(card_height, 200), ThemeColor.BG_DARK)

    cb.set_color(ThemeColor.INFO).set_font(renderer.font_title)
    cb.add_text("🌀 当前裂隙", 25, 15)
    cb.draw_line(25, 48, 775, 48, width=2)

    y_offset = 65
    tier_order = {4: 0, 3: 1, 2: 2, 1: 3}
    sorted_fissures = sorted(fissures, key=lambda f: tier_order.get(f.get("tier", 0), 5))

    for i, fissure in enumerate(sorted_fissures):
        bg_color = ThemeColor.BG_CARD if i % 2 == 0 else ThemeColor.BG_CARD_ALT
        cb.draw_rounded_rect(20, y_offset, 760, 68, radius=8, fill=bg_color)

        node = fissure.get("node", "未知节点")
        mission_type = fissure.get("mission_type", "未知")
        cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(renderer.font_body)
        cb.add_text(f"{node}  [{mission_type}]", 35, y_offset + 10)

        tier_name = fissure.get("tier_name", "")
        if tier_name:
            cb.set_color(ThemeColor.ACCENT).set_font(renderer.font_small)
            cb.add_text(tier_name, 35, y_offset + 38)

        faction = fissure.get("faction", "")
        if faction:
            if renderer.font_wf_icon:
                icon, faction_color = CardRenderer.resolve_faction_icon_and_color(faction)
                if icon:
                    cb.set_color(faction_color).set_font(renderer.font_wf_icon)
                    cb.add_text(icon, 640, y_offset + 2)
            cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(renderer.font_small)
            cb.add_text(faction, 685, y_offset + 10)

        eta = fissure.get("eta", "")
        if eta:
            cb.set_color(ThemeColor.ACCENT_GOLD).set_font(renderer.font_small)
            cb.add_text(eta, 640, y_offset + 38)

        y_offset += item_height

    return cb.to_image()
