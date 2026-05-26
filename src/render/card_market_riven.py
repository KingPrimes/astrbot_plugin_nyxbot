"""Market 紫卡卡片渲染器 — 全新设计 (1.3x 放大版)

布局：
  - 1950px 宽，3 列圆角卡片网格
  - 单卡 576×572 px，BG_CARD 圆角 + 边框
  - 顶部：武器名 + 紫卡后缀 + 极性图标（PolarityEnum.icon）+ MR 徽章
  - 中部：词条列表，元素词条带 ElementEnum 图标 + 颜色
  - 底部：mod 等级点 + 买断价（IconEnum.PLATINUM）+ 起拍/最高/直购徽章 + 卖家信息
  - 深色主题 + 双层装饰边框 + 底部署名 + 看板娘自适应位置

注：本次相对初版整体等比例放大约 1.3x，便于阅读。如需再次调整，
所有字号 / 尺寸常量定义在文件顶部及 _draw_riven_card 内的局部偏移。
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PIL import Image, ImageFont

from ..wenum.element import ElementEnum
from ..wenum.icon import IconEnum
from .draw_constant import DrawConstant, ThemeColor, hex_to_rgb
from .font_manager import FontManager
from .image_combiner import ImageCombiner
from .standing import draw_standing_at

if TYPE_CHECKING:
    from ..model.market import MarketRiven, RivenAttribute, RivenAuction
    from .card_renderer import CardRenderer


# ---------------------------------------------------------------------------
# 布局常量 / Layout constants (1.3x scaled)
# ---------------------------------------------------------------------------

_CANVAS_W = 1950
_MARGIN = 52
_CONTENT_PAD = 26
_CONTENT_X = _MARGIN + _CONTENT_PAD              # 78
_CONTENT_W = _CANVAS_W - 2 * _CONTENT_X          # 1794

_COLS = 3
_COL_GAP = 32
_CARD_W = (_CONTENT_W - _COL_GAP * (_COLS - 1)) // _COLS  # 576
_CARD_H = 572
_CARD_RADIUS = 20
_CARD_PAD = 26
_ROW_GAP = 26

_TITLE_Y = 90
_SUBTITLE_Y = 170
_SUBTITLE_DIVIDER_OFFSET = 65
_CONTENT_START_Y = 260

# 卡片内分区 y 偏移（相对 card_y） / Per-card y offsets
_CARD_HEADER_END = 107
_CARD_ATTR_START = 132
_CARD_ATTR_LINE_H = 44
_CARD_ATTR_END = 364
_CARD_PRICE_DOTS_Y = 385
_CARD_PRICE_BUYOUT_Y = 380
_CARD_PRICE_META_Y = 432
_CARD_FOOTER_LINE = 484
_CARD_OWNER_Y = 504

# 看板娘 / Standing
_STANDING_INROW_W, _STANDING_INROW_H = 420, 520
_STANDING_BELOW_W, _STANDING_BELOW_H = 340, 494

_FOOTER_OFFSET = 72

_RIVEN_SUFFIX_COLOR = (134, 105, 167)  # #8669A7

# 词条 url_name → ElementEnum 映射 / Riven attribute → element
_RIVEN_ELEMENT_MAP: dict[str, ElementEnum] = {
    "cold_damage": ElementEnum.COLD,
    "electric_damage": ElementEnum.ELECTRICITY,
    "toxin_damage": ElementEnum.TOXIN,
    "heat_damage": ElementEnum.HEAT,
    "impact_damage": ElementEnum.IMPACT,
    "puncture_damage": ElementEnum.PUNCTURE,
    "slash_damage": ElementEnum.SLASH,
}

_STATUS_LABEL: dict[str, str] = {
    "online": "在线",
    "ingame": "游戏中",
    "offline": "离线",
    "invisible": "隐身",
}


# ---------------------------------------------------------------------------
# 辅助函数 / Helpers
# ---------------------------------------------------------------------------

def _resolve_attribute(
    attr: RivenAttribute,
) -> tuple[str, tuple[int, int, int], str, bool]:
    """解析词条 → (展示名, RGB 颜色, 元素图标字形 | "", 是否元素)。
    Resolve riven attribute to (display name, RGB color, element glyph or "", is_element).
    """
    url_name = (attr.url_name or "").lower()
    positive = bool(attr.positive)
    elem = _RIVEN_ELEMENT_MAP.get(url_name)
    if elem is not None:
        return f"{elem.display_name}伤害", hex_to_rgb(elem.color), elem.icon, True
    fallback = attr.url_name or "未知词条"
    color = ThemeColor.SUCCESS if positive else ThemeColor.DANGER
    return fallback, color, "", False


def _status_color(status: str | None) -> tuple[int, int, int]:
    """卖家在线状态颜色映射。/ Seller status → color."""
    if not status:
        return ThemeColor.TEXT_MUTED
    s = status.lower()
    if s in ("online", "ingame"):
        return ThemeColor.SUCCESS
    return ThemeColor.TEXT_MUTED


def _format_dots(rank: int | None, max_rank: int = 8) -> str:
    """生成 mod 等级实心/空心点字符串。/ Render mod rank as filled/empty dots."""
    if rank is None or rank < 0:
        rank = 0
    rank = min(rank, max_rank)
    return "●" * rank + "○" * (max_rank - rank)


def _truncate(cb: ImageCombiner, text: str, max_w: int) -> str:
    """按当前字体截断字符串到 max_w 内，必要时追加省略号。"""
    if cb.get_string_width(text) <= max_w:
        return text
    ellipsis = "…"
    while text and cb.get_string_width(text + ellipsis) > max_w:
        text = text[:-1]
    return text + ellipsis if text else ellipsis


# ---------------------------------------------------------------------------
# 单卡片绘制 / Single-card draw
# ---------------------------------------------------------------------------

def _draw_riven_card(
    cb: ImageCombiner,
    auction: RivenAuction,
    item_name: str,
    card_x: int,
    card_y: int,
    fonts: dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont],
) -> None:
    """绘制单张紫卡卡片到主画布。/ Draw a single riven card onto the canvas."""
    rim = auction.item
    inner_x = card_x + _CARD_PAD
    inner_right = card_x + _CARD_W - _CARD_PAD
    inner_w = inner_right - inner_x

    # 卡片背景 + 边框
    cb.draw_rounded_rect(
        card_x, card_y, _CARD_W, _CARD_H,
        radius=_CARD_RADIUS,
        fill=ThemeColor.BG_CARD,
        outline=ThemeColor.TABLE_BORDER,
        stroke_width=1,
    )

    if rim is None:
        cb.set_color(ThemeColor.TEXT_MUTED).set_font(fonts["body"])
        cb.add_text("数据缺失", inner_x, card_y + _CARD_H // 2)
        return

    # 右上角：极性图标 + MR 徽章
    polarity_glyph = rim.polarity.icon if rim.polarity is not None else ""
    polarity_w = 0
    if polarity_glyph:
        cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(fonts["polarity"])
        polarity_w = cb.get_string_width(polarity_glyph)
        cb.add_text(polarity_glyph, inner_right - polarity_w, card_y + 18)

    mr_badge_w = 0
    if rim.mastery_level is not None:
        cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(fonts["badge"])
        mr_text = f"MR{rim.mastery_level}"
        mr_w = cb.get_string_width(mr_text)
        mr_badge_w = mr_w + 18
        cb.add_text_with_background(
            mr_text,
            inner_right - polarity_w - 13 - mr_badge_w,
            card_y + 31,
            bg_color=ThemeColor.BG_CARD_ALT,
            border_color=ThemeColor.DIVIDER,
            corner_radius=8,
            padding=6,
        )

    # 标题区：武器名 + 紫卡后缀
    title_max_w = inner_w - polarity_w - mr_badge_w - 21
    cb.set_color(ThemeColor.ACCENT_GOLD).set_font(fonts["weapon"])
    cb.add_text(_truncate(cb, item_name, title_max_w), inner_x, card_y + 23)

    if rim.name:
        cb.set_color(_RIVEN_SUFFIX_COLOR).set_font(fonts["suffix"])
        cb.add_text(_truncate(cb, rim.name, title_max_w), inner_x, card_y + 65)

    # 分隔线 1
    cb.set_color(ThemeColor.DIVIDER)
    cb.draw_line(
        inner_x, card_y + _CARD_HEADER_END,
        inner_right, card_y + _CARD_HEADER_END,
        width=1,
    )

    # 词条区
    attrs = list(rim.attributes or [])[:5]
    attr_y = card_y + _CARD_ATTR_START
    for attr in attrs:
        name, color, icon_glyph, is_elem = _resolve_attribute(attr)
        val = attr.value if attr.value is not None else 0.0
        positive = bool(attr.positive)
        sign = "+" if val >= 0 else ""
        val_text = f"{sign}{val:.1f}%"

        cb.set_color(color)
        if is_elem and icon_glyph:
            cb.set_font(fonts["attr_icon"])
            icon_w = cb.get_string_width(icon_glyph)
            cb.add_text(icon_glyph, inner_x, attr_y - 5)
            cursor_x = inner_x + max(icon_w, 28) + 8
        else:
            cb.set_font(fonts["attr_arrow"])
            arrow = "▲" if positive else "▼"
            arrow_w = cb.get_string_width(arrow)
            cb.add_text(arrow, inner_x, attr_y)
            cursor_x = inner_x + arrow_w + 10

        # 数值
        cb.set_color(color).set_font(fonts["attr_val"])
        cb.add_text(val_text, cursor_x, attr_y - 3)
        val_w = cb.get_string_width(val_text)

        # 名字
        cb.set_color(color).set_font(fonts["attr"])
        name_x = cursor_x + val_w + 13
        cb.add_text(_truncate(cb, name, inner_right - name_x), name_x, attr_y)

        attr_y += _CARD_ATTR_LINE_H

    # 分隔线 2
    cb.set_color(ThemeColor.DIVIDER)
    cb.draw_line(
        inner_x, card_y + _CARD_ATTR_END,
        inner_right, card_y + _CARD_ATTR_END,
        width=1,
    )

    # 价格 + 元数据
    # 左侧：mod_rank dots
    cb.set_color(ThemeColor.CYCLE_COLD).set_font(fonts["dots"])
    dots_text = _format_dots(rim.mod_rank, 8)
    cb.add_text(dots_text, inner_x, card_y + _CARD_PRICE_DOTS_Y)
    dots_w = cb.get_string_width(dots_text)

    # 左侧次行：循环次数 + 直购徽章
    cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(fonts["meta"])
    rr_text = f"循环 {rim.re_rolls if rim.re_rolls is not None else 0}"
    cb.add_text(rr_text, inner_x, card_y + _CARD_PRICE_META_Y)
    rr_w = cb.get_string_width(rr_text)

    if auction.is_direct_sell:
        cb.set_color(ThemeColor.ACCENT_GREEN).set_font(fonts["badge"])
        cb.add_text_with_background(
            "直购",
            inner_x + rr_w + 16,
            card_y + _CARD_PRICE_META_Y - 1,
            bg_color=ThemeColor.BG_CARD_ALT,
            border_color=ThemeColor.ACCENT_GREEN,
            corner_radius=8,
            padding=5,
        )

    # 右侧：买断价（数字 + 白金图标）
    cb.set_color(ThemeColor.ACCENT_GOLD)
    if auction.buyout_price is not None:
        num_text = str(auction.buyout_price)
        cb.set_font(fonts["price"])
        num_w = cb.get_string_width(num_text)

        plat_glyph = IconEnum.PLATINUM.icon
        cb.set_font(fonts["price_icon"])
        plat_w = cb.get_string_width(plat_glyph)

        gap = 10
        total_w = num_w + gap + plat_w
        x_base = inner_right - total_w

        cb.set_font(fonts["price"])
        cb.add_text(num_text, x_base, card_y + _CARD_PRICE_BUYOUT_Y)
        cb.set_font(fonts["price_icon"])
        cb.add_text(plat_glyph, x_base + num_w + gap, card_y + _CARD_PRICE_BUYOUT_Y)
    else:
        cb.set_font(fonts["price"])
        nego = "议价"
        nw = cb.get_string_width(nego)
        cb.add_text(nego, inner_right - nw, card_y + _CARD_PRICE_BUYOUT_Y)

    # 右侧次行：起拍 / 最高
    sub_parts: list[str] = []
    if auction.starting_price is not None:
        sub_parts.append(f"起拍 {auction.starting_price}")
    if auction.top_bid is not None:
        sub_parts.append(f"最高 {auction.top_bid}")
    if sub_parts:
        sub_text = "  ·  ".join(sub_parts)
        cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(fonts["meta"])
        sub_w = cb.get_string_width(sub_text)
        max_sub_x = max(inner_x + max(dots_w, rr_w) + 78, inner_right - sub_w)
        cb.add_text(sub_text, max_sub_x, card_y + _CARD_PRICE_META_Y)

    # 分隔线 3
    cb.set_color(ThemeColor.DIVIDER)
    cb.draw_line(
        inner_x, card_y + _CARD_FOOTER_LINE,
        inner_right, card_y + _CARD_FOOTER_LINE,
        width=1,
    )

    # 卖家区
    owner = auction.owner
    seller_name = owner.ingame_name if owner and owner.ingame_name else "未知卖家"
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(fonts["owner"])
    name_text = _truncate(cb, seller_name, 234)
    cb.add_text(name_text, inner_x, card_y + _CARD_OWNER_Y)
    name_w = cb.get_string_width(name_text)

    if owner and owner.status:
        status_color = _status_color(owner.status)
        status_label = _STATUS_LABEL.get(owner.status.lower(), owner.status)
        cb.set_color(status_color).set_font(fonts["badge"])
        cb.add_text_with_background(
            status_label,
            inner_x + name_w + 13,
            card_y + _CARD_OWNER_Y + 5,
            bg_color=ThemeColor.BG_CARD_ALT,
            border_color=status_color,
            corner_radius=8,
            padding=5,
        )

    if owner and owner.reputation is not None:
        rep_text = f"声望 {owner.reputation}"
        cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(fonts["meta"])
        rep_w = cb.get_string_width(rep_text)
        cb.add_text(rep_text, inner_right - rep_w, card_y + _CARD_OWNER_Y + 8)


# ---------------------------------------------------------------------------
# 主渲染函数 / Main render
# ---------------------------------------------------------------------------

def render_market_riven_card(
    renderer: CardRenderer,
    market_riven: MarketRiven,
) -> Image.Image:
    """绘制 Market 紫卡市场卡片 — 3 列圆角卡片网格。

    Args:
        renderer: CardRenderer 实例。
        market_riven: MarketRiven 模型。

    Returns:
        PIL Image 对象。
    """
    pay = market_riven.payload
    if pay is None or not pay.auctions:
        return renderer.create_text_image("当前没有紫卡拍卖数据", 1040, 156)

    auctions = pay.auctions
    item_name = market_riven.item_name or "未知武器"

    # 字体（已整体放大约 1.3x）
    title_font = FontManager.get_text_font(60)
    subtitle_font = FontManager.get_text_font(32)
    footer_font = FontManager.get_text_font(24)

    fonts: dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont] = {
        "weapon": FontManager.get_text_font(28),
        "suffix": FontManager.get_text_font(24),
        "polarity": FontManager.get_wf_icon_font(44),
        "badge": FontManager.get_text_font(18),
        "attr": FontManager.get_text_font(24),
        "attr_val": FontManager.get_text_font(26),
        "attr_arrow": FontManager.get_text_font(24),
        "attr_icon": FontManager.get_wf_icon_font(28),
        "dots": FontManager.get_text_font(26),
        "meta": FontManager.get_text_font(21),
        "price": FontManager.get_text_font(36),
        "price_icon": FontManager.get_wf_icon_font(36),
        "owner": FontManager.get_text_font(26),
        "body": FontManager.get_text_font(21),
    }

    # 布局
    n = len(auctions)
    rows = math.ceil(n / _COLS)
    cards_h = rows * _CARD_H + (rows - 1) * _ROW_GAP
    last_row_count = n - (rows - 1) * _COLS
    last_row_y = _CONTENT_START_Y + (rows - 1) * (_CARD_H + _ROW_GAP)
    standing_in_row = last_row_count < _COLS

    content_end = _CONTENT_START_Y + cards_h
    if standing_in_row:
        canvas_h = max(content_end, last_row_y + _STANDING_INROW_H + _FOOTER_OFFSET + 12)
    else:
        canvas_h = content_end + _STANDING_BELOW_H + _FOOTER_OFFSET + 26

    cb = ImageCombiner(_CANVAS_W, canvas_h, ThemeColor.BG_DARK)
    cb.draw_double_border(
        border_padding=20,
        border_color_outer=ThemeColor.TABLE_BORDER,
        border_color_inner=ThemeColor.DIVIDER,
        stroke=3,
    )

    # 标题 + 副标题
    cb.set_color(ThemeColor.ACCENT_GOLD).set_font(title_font)
    cb.add_centered_text("Warframe Market 紫卡市场", _TITLE_Y)
    cb.set_color(_RIVEN_SUFFIX_COLOR).set_font(subtitle_font)
    cb.add_centered_text(item_name, _SUBTITLE_Y)

    # 标题下方分隔线
    cb.set_color(ThemeColor.DIVIDER)
    cb.draw_line(
        _CONTENT_X, _SUBTITLE_Y + _SUBTITLE_DIVIDER_OFFSET,
        _CONTENT_X + _CONTENT_W, _SUBTITLE_Y + _SUBTITLE_DIVIDER_OFFSET,
        width=1,
    )

    # 卡片网格
    col_xs = [_CONTENT_X + i * (_CARD_W + _COL_GAP) for i in range(_COLS)]
    for i, auction in enumerate(auctions):
        row = i // _COLS
        col = i % _COLS
        card_x = col_xs[col]
        card_y = _CONTENT_START_Y + row * (_CARD_H + _ROW_GAP)
        _draw_riven_card(cb, auction, item_name, card_x, card_y, fonts)

    # 看板娘 — 尾行有空位时固定置于最右列，避免 1 个数据时跑到中间
    if standing_in_row:
        rightmost_col = _COLS - 1
        standing_x = col_xs[rightmost_col] + (_CARD_W - _STANDING_INROW_W) // 2
        draw_standing_at(cb, standing_x, last_row_y,
                         _STANDING_INROW_W, _STANDING_INROW_H)
    else:
        standing_x = _CONTENT_X + _CONTENT_W - _STANDING_BELOW_W - 26
        draw_standing_at(cb, standing_x, content_end + 12,
                         _STANDING_BELOW_W, _STANDING_BELOW_H)

    # Footer
    cb.set_color(ThemeColor.TEXT_MUTED).set_font(footer_font)
    cb.add_centered_text(DrawConstant.FOOTER_TEXT, canvas_h - _FOOTER_OFFSET)

    return cb.to_image()
