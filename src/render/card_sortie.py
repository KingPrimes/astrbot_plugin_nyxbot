"""突击卡片渲染器

从 CardRenderer 拆分出的 create_sortie_card 独立实现。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image

from .draw_constant import ThemeColor
from .image_combiner import ImageCombiner

if TYPE_CHECKING:
    from ..model.world_state import Sortie
    from .card_renderer import CardRenderer


def render_sortie_card(renderer: CardRenderer, sortie: Sortie) -> Image.Image:
    """绘制突击信息卡片。

    Args:
        renderer: CardRenderer 实例（提供字体等资源）。
        sortie: Sortie 模型。
    """
    card_width = 800
    item_height = 130
    card_height = 60 + len(sortie.variants) * item_height + 20

    cb = ImageCombiner(card_width, max(card_height, 200), ThemeColor.BG_DARK)

    cb.set_color(ThemeColor.ACCENT_GOLD).set_font(renderer.font_title)
    cb.add_text("⚡ 今日突击", 25, 15)
    cb.draw_line(25, 48, 775, 48, width=2)

    y_offset = 65
    for i, v in enumerate(sortie.variants):
        bg_color = ThemeColor.BG_CARD if i % 2 == 0 else ThemeColor.BG_CARD_ALT
        cb.draw_rounded_rect(20, y_offset, 760, 115, radius=8, fill=bg_color)

        # 阶段标题（使用 modifier_type 名称）
        variant_name = v.modifier_type.name if v.modifier_type else f"阶段 {i + 1}"
        cb.set_color(ThemeColor.ACCENT_BLUE).set_font(renderer.font_subtitle)
        cb.add_text(variant_name, 35, y_offset + 10)

        # 任务节点（已由 Service 翻译）
        node = v.node or "未知节点"
        mission_type = v.mission_type.name if v.mission_type else "未知任务"
        cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(renderer.font_body)
        cb.add_text(f"{node}  —  {mission_type}", 35, y_offset + 40)

        # 特殊规则（modifier_type 名称）
        if v.modifier_type:
            cb.set_color(ThemeColor.ACCENT_GOLD).set_font(renderer.font_small)
            cb.add_text(f"规则: {v.modifier_type.name}", 35, y_offset + 70)

        y_offset += item_height

    return cb.to_image()
