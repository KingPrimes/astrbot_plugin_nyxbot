"""仲裁卡片渲染器

从 CardRenderer 拆分出的 create_arbitration_card 独立实现。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image

from .draw_constant import ThemeColor
from .image_combiner import ImageCombiner

if TYPE_CHECKING:
    from .card_renderer import CardRenderer


def render_arbitration_card(renderer: CardRenderer, arbitration: dict) -> Image.Image:
    """绘制仲裁信息卡片。

    Args:
        renderer: CardRenderer 实例（提供字体等资源）。
        arbitration: 仲裁数据 dict。
    """
    card_width = 800
    card_height = 200

    cb = ImageCombiner(card_width, card_height, ThemeColor.BG_DARK)

    cb.set_color(ThemeColor.ACCENT_GOLD).set_font(renderer.font_title)
    cb.add_text("🏅 当前仲裁", 25, 15)
    cb.draw_line(25, 48, 775, 48, width=2)

    node = arbitration.get("node", "未知节点")
    mission_type = arbitration.get("mission_type", "未知任务")
    faction = arbitration.get("faction", "未知派系")

    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(renderer.font_body)
    cb.add_text(node, 35, 70)

    # 派系图标
    if faction and renderer.font_wf_icon:
        icon, faction_color = CardRenderer.resolve_faction_icon_and_color(faction)
        if icon:
            cb.set_color(faction_color).set_font(renderer.font_wf_icon)
            cb.add_text(icon, 35, 93)

    mt_color = CardRenderer.resolve_mission_type_color(mission_type)
    cb.set_color(mt_color).set_font(renderer.font_small)
    cb.add_text(f"{mission_type}  |  {faction}", 80 if (faction and renderer.font_wf_icon) else 35, 100)

    eta = arbitration.get("eta", "")
    if eta:
        cb.set_color(ThemeColor.ACCENT).set_font(renderer.font_small)
        cb.add_text(f"剩余: {eta}", 640, 70)

    return cb.to_image()
