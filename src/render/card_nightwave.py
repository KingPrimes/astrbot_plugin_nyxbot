"""午夜电波卡片渲染器

从 CardRenderer 拆分出的 create_nightwave_card 独立实现。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image

from .draw_constant import ThemeColor
from .image_combiner import ImageCombiner

if TYPE_CHECKING:
    from ..model.world_state import SeasonInfo
    from .card_renderer import CardRenderer


def render_nightwave_card(renderer: CardRenderer, nightwave: SeasonInfo) -> Image.Image:
    """绘制午夜电波卡片。

    Args:
        renderer: CardRenderer 实例（提供字体等资源）。
        nightwave: SeasonInfo 模型。
    """
    card_width = 800
    item_height = 50
    card_height = 80 + len(nightwave.active_challenges) * item_height + 20

    cb = ImageCombiner(card_width, max(card_height, 150), ThemeColor.BG_DARK)

    cb.set_color(ThemeColor.ACCENT_BLUE).set_font(renderer.font_title)
    cb.add_text("📡 午夜电波", 25, 15)

    season = str(nightwave.season) if nightwave.season else ""
    if season:
        cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(renderer.font_small)
        cb.add_text(f"第 {season} 季", 640, 15)

    cb.draw_line(25, 48, 775, 48, width=2)

    y_offset = 85
    if nightwave.active_challenges:
        for i, ac in enumerate(nightwave.active_challenges):
            bg_color = ThemeColor.BG_CARD if i % 2 == 0 else ThemeColor.BG_CARD_ALT
            cb.draw_rounded_rect(20, y_offset, 760, 42, radius=6, fill=bg_color)

            title = ac.name or ac.challenge or "未知任务"
            standing = ac.standing or 0
            is_daily = ac.daily or False
            is_elite = ac.elite or False

            prefix = "🔥 " if is_elite else ("📅 " if is_daily else "")
            cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(renderer.font_small)
            cb.add_text(f"{prefix}{title}", 35, y_offset + 8)

            label = "精英" if is_elite else ("日常" if is_daily else "周常")
            label_color = ThemeColor.ACCENT_GOLD if is_elite else ThemeColor.TEXT_SECONDARY
            cb.set_color(label_color).set_font(renderer.font_tiny)
            cb.add_text(f"{standing} 声望  [{label}]", 640, y_offset + 8)

            y_offset += item_height

    return cb.to_image()
