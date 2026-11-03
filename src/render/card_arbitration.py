"""仲裁卡片渲染器 — 对齐 Go draw_arbitration.go

布局：
  - 单条：左侧 850×210 卡片（节点/敌人、任务类型/开始、剩余/评级）+ 右侧看板娘
  - 列表：两列卡片网格（最多 10 条）+ 看板娘
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image, ImageFont

from ..wenum.faction import FactionEnum
from .draw_constant import ThemeColor, hex_to_rgb
from .font_manager import FontManager
from .image_combiner import ImageCombiner
from .standing import draw_standing_at

if TYPE_CHECKING:
    from ..model.arbitration import ArbitrationView
    from .card_renderer import CardRenderer

# 单条卡片 / Single card
_SINGLE_CANVAS_W = 1450
_SINGLE_CANVAS_H = 470
_CARD_X = 50
_CARD_Y = 150
_CARD_W = 850
_CARD_H = 210
_CARD_RADIUS = 14
_CARD_PAD = 24
_ROW_H = 52
_TITLE_Y = 80

# 前瞻列表 / Arbitration list
_LIST_CANVAS_W = 1300
_LIST_CONTENT_X = 50
_LIST_CONTENT_W = 1200
_LIST_COLS = 2
_LIST_GAP = 20
_LIST_CARD_H = 190
_LIST_ROW_GAP = 20
_LIST_CARD_PAD = 20
_LIST_CARD_ROW_H = 44
_LIST_START_Y = 160

# 评级颜色 — 对齐 Go tierSColor..tierFColor
_TIER_COLORS: dict[str, tuple[int, int, int]] = {
    "S": (0xFF, 0xC1, 0x07),
    "A": (0xE0, 0x40, 0xFB),
    "B": (0x42, 0xA5, 0xF5),
    "C": (0x66, 0xBB, 0x6A),
    "D": (0x9E, 0x9E, 0x9E),
    "F": (0x75, 0x75, 0x75),
}


def _tier_label(tier: str) -> str:
    """评级显示文本：空值/未知值按 F 渲染。"""
    normalized = (tier or "").strip().upper()
    return normalized if normalized in _TIER_COLORS else "F"


def _tier_color(tier: str) -> tuple[int, int, int]:
    """评级颜色：空值/未知值按 F 渲染。"""
    return _TIER_COLORS[_tier_label(tier)]


def _faction_label(faction: FactionEnum) -> str:
    """派系显示名；未知派系回退“未知”。"""
    if faction is FactionEnum.FC_NONE:
        return "未知"
    return faction.display_name or "未知"


def _draw_card(
    cb: ImageCombiner,
    view: ArbitrationView,
    card_x: int,
    card_y: int,
    card_w: int,
    card_h: int,
    *,
    pad: int,
    row_h: int,
    data_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    tier_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    icon_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """绘制单张仲裁卡片（三行布局）。"""
    cb.set_color(ThemeColor.BG_CARD).draw_rounded_rect(
        card_x, card_y, card_w, card_h, radius=_CARD_RADIUS
    )

    inner_x = card_x + pad
    inner_w = card_w - pad * 2
    right_x = inner_x + inner_w // 2 + 10
    row1_y = card_y + 45
    row2_y = row1_y + row_h
    row3_y = row2_y + row_h

    # 第一行：节点 | 敌人
    node = view.node or "未知节点"
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(data_font)
    cb.add_text(f"节点: {node}", inner_x, row1_y)

    faction = view.faction
    info = _faction_label(faction)
    cursor = right_x
    if faction is not FactionEnum.FC_NONE and faction.icon:
        cb.set_color(hex_to_rgb(faction.color)).set_font(icon_font)
        cb.add_text(faction.icon, cursor, row1_y)
        cursor += int(cb.draw.textlength(faction.icon, font=icon_font)) + 4
    cb.set_color(hex_to_rgb(faction.color)).set_font(data_font)
    cb.add_text(f"敌人: {info}", cursor, row1_y)

    # 第二行：任务类型 | 开始时间
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(data_font)
    cb.add_text(f"任务类型: {view.mission_name or '未知'}", inner_x, row2_y)
    cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(data_font)
    cb.add_text(f"开始: {view.activation_str}", right_x, row2_y)

    # 第三行：剩余时间 | 评级
    cb.set_color(ThemeColor.ACCENT_GOLD).set_font(data_font)
    cb.add_text(f"剩余: {view.time_left}", inner_x, row3_y)
    cb.set_color(_tier_color(view.tier)).set_font(tier_font)
    cb.add_text(f"评级: {_tier_label(view.tier)}", right_x, row3_y)


def render_arbitration_card(
    renderer: CardRenderer,
    arbitration: ArbitrationView,
) -> Image.Image:
    """绘制单条仲裁卡片 — 对齐 Go DrawArbitration。"""
    if arbitration is None:
        return renderer.create_text_image("仲裁数据为空", 800, 120)

    cb = ImageCombiner(_SINGLE_CANVAS_W, _SINGLE_CANVAS_H, ThemeColor.BG_DARK)
    cb.draw_double_border(
        border_padding=12,
        border_color_outer=ThemeColor.TABLE_BORDER,
        border_color_inner=ThemeColor.DIVIDER,
        stroke=2,
    )

    cb.set_color(ThemeColor.ACCENT_BLUE).set_font(
        FontManager.get_text_font(36)
    )
    cb.add_text("仲裁任务", _CARD_X, _TITLE_Y)
    cb.set_color(ThemeColor.DIVIDER)
    cb.draw_line(
        _CARD_X,
        _TITLE_Y + 55,
        _CARD_X + _CARD_W,
        _TITLE_Y + 55,
        width=1,
    )

    _draw_card(
        cb,
        arbitration,
        _CARD_X,
        _CARD_Y,
        _CARD_W,
        _CARD_H,
        pad=_CARD_PAD,
        row_h=_ROW_H,
        data_font=FontManager.get_text_font(24),
        tier_font=FontManager.get_text_font(28),
        icon_font=FontManager.get_wf_icon_font(32),
    )

    draw_standing_at(cb, 1120, _CARD_Y, 300, 300)
    cb.draw_card_footer(_SINGLE_CANVAS_H, 30, 18)
    return cb.to_image()


def render_arbitration_list_card(
    renderer: CardRenderer,
    arbitrations: list[ArbitrationView],
) -> Image.Image:
    """绘制仲裁前瞻列表 — 对齐 Go DrawArbitrations。"""
    if not arbitrations:
        return renderer.create_text_image("暂无可参与的仲裁数据", 800, 120)

    cards = arbitrations[:10]
    card_w = (_LIST_CONTENT_W - _LIST_GAP) // _LIST_COLS
    rows = (len(cards) + _LIST_COLS - 1) // _LIST_COLS
    cards_h = rows * _LIST_CARD_H + (rows - 1) * _LIST_ROW_GAP
    odd = len(cards) % _LIST_COLS != 0

    standing_x = _LIST_CONTENT_X + card_w + _LIST_GAP
    standing_y = _LIST_START_Y + cards_h + 10
    if odd:
        standing_x = _LIST_CONTENT_X + card_w + _LIST_GAP
        standing_y = _LIST_START_Y + (rows - 1) * (
            _LIST_CARD_H + _LIST_ROW_GAP
        )
    canvas_h = max(
        standing_y + 300,
        _LIST_START_Y + cards_h + 40,
    )

    cb = ImageCombiner(_LIST_CANVAS_W, canvas_h, ThemeColor.BG_DARK)
    cb.draw_double_border(
        border_padding=12,
        border_color_outer=ThemeColor.TABLE_BORDER,
        border_color_inner=ThemeColor.DIVIDER,
        stroke=2,
    )

    cb.set_color(ThemeColor.ACCENT_BLUE).set_font(
        FontManager.get_text_font(40)
    )
    cb.add_centered_text("有价值的仲裁任务", _TITLE_Y)
    cb.set_color(ThemeColor.DIVIDER)
    cb.draw_line(
        _LIST_CONTENT_X,
        _TITLE_Y + 55,
        _LIST_CONTENT_X + _LIST_CONTENT_W,
        _TITLE_Y + 55,
        width=1,
    )

    data_font = FontManager.get_text_font(20)
    tier_font = FontManager.get_text_font(22)
    icon_font = FontManager.get_wf_icon_font(24)

    for index, view in enumerate(cards):
        row = index // _LIST_COLS
        col = index % _LIST_COLS
        card_x = _LIST_CONTENT_X + col * (card_w + _LIST_GAP)
        card_y = _LIST_START_Y + row * (
            _LIST_CARD_H + _LIST_ROW_GAP
        )
        _draw_card(
            cb,
            view,
            card_x,
            card_y,
            card_w,
            _LIST_CARD_H,
            pad=_LIST_CARD_PAD,
            row_h=_LIST_CARD_ROW_H,
            data_font=data_font,
            tier_font=tier_font,
            icon_font=icon_font,
        )

    draw_standing_at(cb, standing_x, standing_y, 280, 280)
    cb.draw_card_footer(canvas_h, 30, 18)
    return cb.to_image()
