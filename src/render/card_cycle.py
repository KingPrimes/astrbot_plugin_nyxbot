"""周期卡片渲染器

对应 Java DefaultDrawAllCycleImage.java。
使用 Warframe 图标字体渲染状态图标，垂直列表布局。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image

from ..wenum.faction import FactionEnum
from ..wenum.icon import IconEnum
from .draw_constant import ThemeColor
from .image_combiner import ImageCombiner

if TYPE_CHECKING:
    from ..model.world_state.all_cycles import AllCycles
    from .card_renderer import CardRenderer


class _CycleRow:
    """单行周期渲染数据 / Single cycle row rendering data."""
    __slots__ = ("name", "icon_char", "is_warm", "state_text", "time_left")

    def __init__(
        self,
        name: str,
        icon_char: str,
        is_warm: bool,
        state_text: str,
        time_left: str,
    ) -> None:
        self.name = name
        self.icon_char = icon_char
        self.is_warm = is_warm
        self.state_text = state_text
        self.time_left = time_left


def _build_rows(cycles: AllCycles) -> list[_CycleRow]:
    """从 AllCycles 构建渲染行列表 / Build row list from AllCycles data.

    逻辑对应 Java DefaultDrawAllCycleImage:
    - Earth/Cetus: is_day → warm+SUN, else cold+NIGHT
    - Vallis: is_warm → warm+SUN, else cold+COLD
    - Cambion: active=="FASS" → warm+SUN, else cold+NIGHT
    - Zariman: is_corpus → warm+FC_GRINEER, else cold+FC_CORPUS
    """
    rows: list[_CycleRow] = []

    if cycles.earth:
        icon = IconEnum.SUN.icon if cycles.earth.is_day else IconEnum.NIGHT.icon
        rows.append(_CycleRow(
            "地球",
            icon,
            cycles.earth.is_day,
            cycles.earth.state,
            cycles.earth.time_left,
        ))

    if cycles.cetus:
        icon = IconEnum.SUN.icon if cycles.cetus.is_day else IconEnum.NIGHT.icon
        rows.append(_CycleRow(
            "希图斯（夜灵平野）",
            icon,
            cycles.cetus.is_day,
            cycles.cetus.state,
            cycles.cetus.time_left,
        ))

    if cycles.vallis:
        icon = IconEnum.SUN.icon if cycles.vallis.is_warm else IconEnum.COLD.icon
        rows.append(_CycleRow(
            "福尔图娜（奥布山谷）",
            icon,
            cycles.vallis.is_warm,
            cycles.vallis.state,
            cycles.vallis.time_left,
        ))

    if cycles.cambion:
        is_fass = cycles.cambion.active == "FASS"
        icon = IconEnum.SUN.icon if is_fass else IconEnum.NIGHT.icon
        rows.append(_CycleRow(
            "魔胎之境（火卫二）",
            icon,
            is_fass,
            cycles.cambion.active,
            cycles.cambion.time_left,
        ))

    if cycles.zariman:
        icon = FactionEnum.FC_GRINEER.icon if cycles.zariman.is_corpus else FactionEnum.FC_CORPUS.icon
        rows.append(_CycleRow(
            "扎里曼号",
            icon,
            cycles.zariman.is_corpus,
            cycles.zariman.state,
            cycles.zariman.time_left,
        ))

    return rows


def render_cycle_card(
    renderer: CardRenderer,
    cycles: AllCycles,
    title: str = "平原周期",
) -> Image.Image:
    """绘制周期信息卡片。

    Args:
        renderer: CardRenderer 实例（提供字体等资源）。
        cycles: AllCycles 聚合对象。
        title: 卡片标题。
    """
    rows = _build_rows(cycles)
    if not rows:
        return renderer.create_text_image("无周期数据")

    # 布局常量
    card_width = 800
    row_height = 88
    card_padding_top = 60
    card_padding_bottom = 20
    card_height = card_padding_top + len(rows) * row_height + card_padding_bottom

    cb = ImageCombiner(card_width, max(card_height, 150), ThemeColor.BG_DARK)

    # 标题
    cb.set_color(ThemeColor.ACCENT_GREEN).set_font(renderer.font_title)
    cb.add_text(title, 25, 15)
    cb.draw_line(25, 48, 775, 48, width=2)

    # 加载大号图标字体（回退到文本字体兜底）
    icon_font = renderer.font_wf_icon_large
    if icon_font is None:
        icon_font = renderer.font_wf_icon
    if icon_font is None:
        icon_font = renderer.font_body

    y_offset = 65
    for i, row in enumerate(rows):
        bg_color = ThemeColor.BG_CARD if i % 2 == 0 else ThemeColor.BG_CARD_ALT
        cb.draw_rounded_rect(20, y_offset, 760, row_height - 8, radius=8, fill=bg_color)

        # 状态颜色 — warm=金色, cold=蓝色
        state_color = ThemeColor.CYCLE_WARM if row.is_warm else ThemeColor.CYCLE_COLD

        # 大号图标（居中于行）
        icon_size = 56
        icon_x = 45
        icon_y = y_offset + (row_height - 8 - icon_size) // 2
        cb.set_color(state_color)
        saved_font = cb.current_font
        cb.set_font(icon_font).add_text(row.icon_char, icon_x, icon_y)
        cb.set_font(saved_font)

        # 地点名称
        text_x = 115
        cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(renderer.font_body)
        cb.add_text(row.name, text_x, y_offset + 14)

        # 状态文字
        cb.set_color(state_color).set_font(renderer.font_small)
        cb.add_text(row.state_text, text_x, y_offset + 44)

        # 剩余时间（右对齐）
        if row.time_left:
            time_text = f"剩余: {row.time_left}"
            cb.set_color(ThemeColor.ACCENT).set_font(renderer.font_small)
            cb.add_text(time_text, 640, y_offset + 14)

        y_offset += row_height

    return cb.to_image()
