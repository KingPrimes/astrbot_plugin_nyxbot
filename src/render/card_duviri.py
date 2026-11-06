"""双衍王境卡片渲染器

版式：页头 + 键值（当前情绪 / 剩余时间）+ 左右两列选择项卡片 + 看板娘 + 署名。
情绪按名称着色；选择项按「普通 / 钢铁之路」分列，两列等高。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from . import card_frame as frame
from . import components as C
from .card_size import CardSpec, CustomBlock, KvBlock, measure_card_size
from .design import FONT, SPACE, adapt_color, font
from .theme import current_theme

if TYPE_CHECKING:
    from PIL import Image

    from ..model.world_state.duvalier_cycle import DuvalierCycle
    from .card_renderer import CardRenderer

#: 情绪 → 语义色（会按主题校正对比度）。
_EMOTION_COLORS: dict[str, str] = {
    "悲伤": "#4A90D9",
    "恐惧": "#9B59B6",
    "喜悦": "#F1C40F",
    "愤怒": "#E74C3C",
    "嫉妒": "#2ECC71",
}

#: 区块内边距、行高（与绘制同口径）。
_PAD = SPACE["lg"]
_TITLE_OFFSET = SPACE["md"]
_DIVIDER_OFFSET = _TITLE_OFFSET + FONT["base"] + SPACE["sm"]
_ITEMS_OFFSET = _DIVIDER_OFFSET + SPACE["md"]
_ITEM_H = FONT["sm"] + SPACE["md"]
_MAX_ITEMS = 7


def _split_choices(choices) -> tuple[list[str], list[str]]:
    normal: list[str] = []
    hard: list[str] = []
    for choice in choices or []:
        category = getattr(choice, "category", None)
        if category is None:
            continue
        value = getattr(category, "value", category)
        if value == "EXC_NORMAL":
            normal.extend(choice.choices)
        elif value == "EXC_HARD":
            hard.extend(choice.choices)
    return normal[:_MAX_ITEMS], hard[:_MAX_ITEMS]


def _draw_column(page, x: int, y: int, w: int, h: int, title: str, accent, items: list[str]) -> None:
    """一列选择项卡片：顶部强调条 + 标题 + 分割线 + 条目。"""
    palette = page.palette
    cb = page.cb
    C.draw_grid_card(page, x, y, w, h)

    cb.set_color(accent)
    cb.draw_rounded_rect(x + 14, y + 2, w - 28, 4, radius=2, fill=accent)

    title_font = font("base")
    title_w = C.measure(title, title_font)
    cb.set_color(accent).set_font(title_font)
    cb.add_text(title, x + (w - title_w) // 2, y + _TITLE_OFFSET)

    cb.set_color(palette.border)
    cb.draw_line(x + _PAD, y + _DIVIDER_OFFSET, x + w - _PAD, y + _DIVIDER_OFFSET, width=1)

    item_font = font("sm")
    bullet = "• "
    bullet_w = C.measure(bullet, item_font)
    item_y = y + _ITEMS_OFFSET
    if not items:
        cb.set_color(palette.text_dim).set_font(item_font)
        cb.add_text("暂无", x + _PAD, item_y)
        return

    for item in items:
        cb.set_color(accent).set_font(item_font)
        cb.add_text(bullet, x + _PAD, item_y)
        cb.set_color(palette.text).set_font(item_font)
        cb.add_text(
            C.fit_text(item, w - _PAD * 2 - bullet_w, item_font),
            x + _PAD + bullet_w,
            item_y,
        )
        item_y += _ITEM_H


def render_duviri_card(
    renderer: CardRenderer,
    duviri: DuvalierCycle,
) -> Image.Image:
    """绘制双衍王境卡片。

    Args:
        renderer: CardRenderer 实例（保留参数以兼容渲染入口）。
        duviri: 双衍王境情绪循环数据。
    """
    if duviri is None:
        return renderer.create_text_image("当前没有双衍王境数据", 800, 120)

    theme = current_theme()
    palette = theme.palette

    emotion = duviri.state or "未知"
    emotion_color = adapt_color(_EMOTION_COLORS.get(emotion, "#5B8DEF"), theme)
    info_rows = [
        ("当前情绪", emotion, emotion_color),
        ("剩余时间", duviri.time_left or "未知", palette.amber),
    ]

    normal_items, hard_items = _split_choices(duviri.choices)
    item_font = font("sm")
    bullet_w = C.measure("• ", item_font)
    longest = max(
        (C.measure(item, item_font) for item in normal_items + hard_items),
        default=0,
    )
    # 列宽由最长条目决定，夹在 [220, 360]，避免一行字把卡撑爆
    column_w = max(220, min(360, longest + bullet_w + _PAD * 2 + SPACE["sm"]))
    max_count = max(len(normal_items), len(hard_items), 1)
    column_h = _ITEMS_OFFSET + max_count * _ITEM_H + SPACE["md"]

    gap = SPACE["lg"]
    size = measure_card_size(
        CardSpec(
            title="双衍王境",
            blocks=[
                KvBlock(info_rows),
                CustomBlock(width=column_w * 2 + gap, height=column_h),
            ],
            standing="md",
        )
    )

    page = C.new_page(theme, size.width, size.height)
    y = C.draw_header(page, "双衍王境")
    y = C.draw_kv(page, info_rows, y + SPACE["md"])

    left_x = page.content_x
    right_x = left_x + column_w + gap
    _draw_column(page, left_x, y, column_w, column_h, "普通", palette.gold, normal_items)
    _draw_column(page, right_x, y, column_w, column_h, "钢铁之路", palette.red, hard_items)

    frame.draw_standing_block(page, y + column_h, "md")
    frame.draw_footer_block(page)
    return page.cb.to_image()
