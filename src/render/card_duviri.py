"""双衍王境卡片渲染器

重新设计的视觉布局，摒弃 Java 表格式：
  - 情绪状态以独立展示卡呈现，各情绪独立配色，带彩色边框
  - 普通/钢铁选择项以两张圆角卡片并列呈现，顶部彩色强调条
  - 双层边框 + 看板娘立绘 + 底部署名
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image, ImageFont

from .draw_constant import ThemeColor
from .font_manager import FontManager
from .image_combiner import ImageCombiner
from .standing import draw_standing

if TYPE_CHECKING:
    from ..model.world_state.duvalier_cycle import DuvalierCycle
    from ..model.world_state.endless_xp_choices import EndlessXpChoices
    from .card_renderer import CardRenderer

# ---------------------------------------------------------------------------
# 布局常量
# ---------------------------------------------------------------------------

_CANVAS_W = 1000
_CANVAS_H = 680

_CONTENT_MARGIN = 60
_STANDING_ZONE = 280                # 右侧留给看板娘的区域
_CONTENT_W = _CANVAS_W - _CONTENT_MARGIN - _STANDING_ZONE

# 选择项卡片
_COL_GAP = 30
_CARD_W = (_CONTENT_W - _COL_GAP) // 2
_LEFT_X = _CONTENT_MARGIN
_RIGHT_X = _CONTENT_MARGIN + _CARD_W + _COL_GAP
_CARD_HEADER_H = 42
_CARD_RADIUS = 14
_ITEM_H = 32
_ITEM_PAD_TOP = 12
_ITEM_PAD_LEFT = 20
_MAX_ITEMS = 7

# 情绪独立配色 — 与情绪名称一一对应
_EMOTION_COLORS: dict[str, tuple[int, int, int]] = {
    "悲伤": (74, 144, 217),
    "恐惧": (155, 89, 182),
    "喜悦": (241, 196, 15),
    "愤怒": (231, 76, 60),
    "嫉妒": (46, 204, 113),
}

# 列强调色
_COLOR_NORMAL = (255, 215, 0)
_COLOR_HARD = (255, 107, 107)


def render_duviri_card(
    renderer: CardRenderer,
    duviri: DuvalierCycle,
) -> Image.Image:
    """绘制双衍王境卡片。

    Args:
        renderer: CardRenderer 实例。
        duviri: 双衍王境情绪循环数据。

    Returns:
        PIL Image 对象。
    """
    if duviri is None:
        return renderer.create_text_image("当前没有双衍王境数据", 800, 120)

    # ---- 字体 ----
    title_font = FontManager.get_text_font(56)
    emotion_font = FontManager.get_text_font(36)
    header_font = FontManager.get_text_font(26)
    body_font = FontManager.get_text_font(22)
    label_font = FontManager.get_text_font(18)
    FontManager.get_text_font(16)

    # ---- 画布 ----
    cb = ImageCombiner(_CANVAS_W, _CANVAS_H, ThemeColor.BG_DARK)
    cb.draw_double_border()

    # ---- 标题 ----
    cb.set_color(ThemeColor.ACCENT_BLUE).set_font(title_font)
    cb.add_centered_text("双衍王境", 36)

    # ---- 分割线 ----
    cb.set_color(ThemeColor.DIVIDER)
    cb.draw_line(_CONTENT_MARGIN, 108, _CANVAS_W - _CONTENT_MARGIN, 108, width=1)

    # ---- 情绪展示卡 ----
    emotion_color = _EMOTION_COLORS.get(duviri.state, ThemeColor.ACCENT_BLUE)

    emotion_card_w = 420
    emotion_card_h = 110
    emotion_card_x = (_CANVAS_W - emotion_card_w) // 2
    emotion_card_y = 130

    cb.set_color(ThemeColor.BG_CARD)
    cb.draw_rounded_rect(emotion_card_x, emotion_card_y, emotion_card_w, emotion_card_h, radius=14)
    cb.draw_rounded_rect(
        emotion_card_x, emotion_card_y, emotion_card_w, emotion_card_h,
        radius=14, fill=None, outline=emotion_color, stroke_width=2,
    )

    cb.set_color(ThemeColor.TEXT_MUTED).set_font(label_font)
    cb.add_centered_text("当前情绪", emotion_card_y + 16)
    cb.set_color(emotion_color).set_font(emotion_font)
    cb.add_centered_text(duviri.state, emotion_card_y + 48)

    # ---- 剩余时间 ----
    time_y = emotion_card_y + emotion_card_h + 24
    cb.set_color(ThemeColor.WARNING).set_font(body_font)
    cb.add_centered_text(f"剩余时间: {duviri.time_left}", time_y)

    # ---- 选择项卡片 ----
    choices_start_y = time_y + 40
    choices = duviri.choices or []

    if choices:
        _draw_choices_section(cb, choices, choices_start_y, header_font, body_font)
    else:
        cb.set_color(ThemeColor.TEXT_MUTED).set_font(body_font)
        cb.add_centered_text("暂无选择项数据", choices_start_y + 40)

    # ---- 看板娘（内容之后绘制，避免被遮挡） ----
    draw_standing(cb, max_w=300, max_h=450)

    # ---- 底部署名 ----
    cb.draw_card_footer(_CANVAS_H, 40, 16)

    return cb.to_image()


# ---------------------------------------------------------------------------
# 选择项绘制
# ---------------------------------------------------------------------------

def _draw_choices_section(
    cb: ImageCombiner,
    choices: list[EndlessXpChoices],
    start_y: int,
    header_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    body_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """绘制双列选择项卡片。"""
    normal_items: list[str] = []
    hard_items: list[str] = []

    for c in choices:
        if c.category is None:
            continue
        if c.category.value == "EXC_NORMAL":
            normal_items.extend(c.choices)
        elif c.category.value == "EXC_HARD":
            hard_items.extend(c.choices)

    # 截断超长列表
    normal_items = normal_items[:_MAX_ITEMS]
    hard_items = hard_items[:_MAX_ITEMS]

    # 两列等高，取最大条目数
    max_count = max(len(normal_items), len(hard_items), 1)
    card_h = _CARD_HEADER_H + _ITEM_PAD_TOP + max_count * _ITEM_H + 16

    _draw_column_card(
        cb, _LEFT_X, start_y, _CARD_W, card_h,
        "普通", _COLOR_NORMAL, normal_items, header_font, body_font,
    )
    _draw_column_card(
        cb, _RIGHT_X, start_y, _CARD_W, card_h,
        "钢铁之路", _COLOR_HARD, hard_items, header_font, body_font,
    )


def _draw_column_card(
    cb: ImageCombiner,
    x: int,
    y: int,
    w: int,
    h: int,
    title: str,
    accent: tuple[int, int, int],
    items: list[str],
    header_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    body_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """绘制单列选择项卡片。

    结构:
      ┌──────────────────┐
      │ ████ 强调条 ████ │  ← 顶部 4px 彩色条
      │    标题 (居中)    │  ← 标题
      │ ─── 分割线 ──── │
      │ • 奖励项1        │
      │ • 奖励项2        │
      │   ...           │
      └──────────────────┘
    """
    # 卡片背景
    cb.set_color(ThemeColor.BG_CARD)
    cb.draw_rounded_rect(x, y, w, h, radius=_CARD_RADIUS)

    # 顶部强调条 — 彩色条带横跨卡片顶部
    cb.set_color(accent)
    cb.fill_rect(x + _CARD_RADIUS, y + 2, w - 2 * _CARD_RADIUS, 4)

    # 标题 — 居中、彩色
    cb.set_color(accent).set_font(header_font)
    title_w_val = cb.get_string_width(title)
    cb.add_text(title, x + (w - title_w_val) // 2, y + 18)

    # 分割线
    cb.set_color(ThemeColor.DIVIDER)
    cb.draw_line(x + 24, y + _CARD_HEADER_H, x + w - 24, y + _CARD_HEADER_H, width=1)

    # 奖励项
    item_y = y + _CARD_HEADER_H + _ITEM_PAD_TOP
    cb.set_font(body_font)

    if not items:
        cb.set_color(ThemeColor.TEXT_MUTED)
        cb.add_text("暂无", x + _ITEM_PAD_LEFT, item_y + 10)
    else:
        for item in items:
            # 小圆点前缀
            cb.set_color(accent)
            cb.add_text("•", x + _ITEM_PAD_LEFT, item_y + 3)
            # 奖励名称
            cb.set_color(ThemeColor.TEXT_PRIMARY)
            cb.add_text(item, x + _ITEM_PAD_LEFT + 14, item_y + 3)
            item_y += _ITEM_H
