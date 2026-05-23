"""入侵卡片渲染器

从 CardRenderer 拆分出的 create_invasion_card 独立实现。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image

from .draw_constant import ThemeColor
from .image_combiner import ImageCombiner

if TYPE_CHECKING:
    from ..model.world_state import Invasion
    from .card_renderer import CardRenderer


def render_invasion_card(renderer: CardRenderer, invasions: list[Invasion]) -> Image.Image:
    """绘制入侵信息卡片。

    Args:
        renderer: CardRenderer 实例（提供字体等资源）。
        invasions: Invasion 模型列表。
    """
    card_width = 800
    item_height = 100
    card_height = 60 + len(invasions) * item_height + 20

    cb = ImageCombiner(card_width, max(card_height, 200), ThemeColor.BG_DARK)

    cb.set_color(ThemeColor.WARNING).set_font(renderer.font_title)
    cb.add_text("⚔ 当前入侵", 25, 15)
    cb.draw_line(25, 48, 775, 48, width=2)

    y_offset = 65
    for i, inv in enumerate(invasions):
        bg_color = ThemeColor.BG_CARD if i % 2 == 0 else ThemeColor.BG_CARD_ALT
        cb.draw_rounded_rect(20, y_offset, 760, 88, radius=8, fill=bg_color)

        node = inv.node or "未知节点"
        cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(renderer.font_body)
        cb.add_text(node, 35, y_offset + 10)

        attacker = inv.faction.name if inv.faction else "未知"
        defender = inv.defender_faction.name if inv.defender_faction else "未知"

        # 攻击方图标
        x_atk = 35
        if inv.faction and renderer.font_wf_icon:
            icon, atk_color = CardRenderer.resolve_faction_icon_and_color(inv.faction)
            if icon:
                cb.set_color(atk_color).set_font(renderer.font_wf_icon)
                cb.add_text(icon, x_atk, y_offset + 30)
                x_atk += 45

        cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(renderer.font_small)
        cb.add_text(f"{attacker}  ⚔  {defender}", x_atk, y_offset + 38)

        # 进度
        completion = int(inv.count or 0)
        progress_color = ThemeColor.SUCCESS if completion > 50 else ThemeColor.WARNING
        cb.set_color(progress_color).set_font(renderer.font_small)
        cb.add_text(f"进度: {completion}", 640, y_offset + 10)

        # 收集奖励物品名（已由 Service 翻译）
        reward_items: list[str] = []
        for rw in inv.attacker_reward:
            if rw.counted_items:
                for ci in rw.counted_items:
                    reward_items.append(ci.name)
        if inv.defender_reward and inv.defender_reward.counted_items:
            for ci in inv.defender_reward.counted_items:
                reward_items.append(ci.name)
        reward_str = ", ".join(reward_items[:4]) if reward_items else ""
        if reward_str:
            cb.set_color(ThemeColor.ACCENT_GOLD).set_font(renderer.font_tiny)
            cb.add_text(f"奖励: {reward_str}", 640, y_offset + 38)

    return cb.to_image()
