"""Market 赤毒/信条卡片渲染器 — 迁移自 Java DefaultDrawMarketLichSisterImage

布局：
  - 1350px 宽
  - 标题（物品名称 + 拍卖信息）
  - 表格列: 元素 / 伤害 / 起拍价 / 买断价 / 卖家 / 声望
  - 深色主题 + 看板娘立绘
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image

from ..wenum.element import ElementEnum
from .draw_constant import ThemeColor, hex_to_rgb
from .font_manager import FontManager
from .image_combiner import ImageCombiner
from .standing import draw_standing

if TYPE_CHECKING:
    from ..model.market import MarketLichSister
    from .card_renderer import CardRenderer

_CANVAS_W = 1350
_MARGIN = 40
_TITLE_H = 60
_HEADER_H = 50
_ROW_H = 60
_FOOTER_H = 40

# 列 X 偏移（相对 _MARGIN） / Column X offsets relative to _MARGIN
_COL_ELEMENT_X = 10
_COL_DAMAGE_X = 200
_COL_START_X = 330
_COL_BUYOUT_X = 480
_COL_SELLER_X = 650
_COL_REP_X = 1000

_UNKNOWN_LABEL = "未知"


def _resolve_element(
    key: str | None,
) -> tuple[str, tuple[int, int, int], str]:
    """解析元素 key → (中文名, RGB 颜色, 图标字形)。
    Resolve element key to (display name, RGB color, icon glyph).

    未知 key 返回安全 fallback，避免崩溃。
    Unknown keys return a safe fallback to avoid crashes.
    """
    if not key:
        return _UNKNOWN_LABEL, ThemeColor.TEXT_SECONDARY, ""
    try:
        member = ElementEnum[key.upper()]
    except KeyError:
        return key, ThemeColor.TEXT_SECONDARY, ""
    return member.display_name, hex_to_rgb(member.color), member.icon


def render_market_lich_sister_card(
    renderer: CardRenderer,
    data: MarketLichSister,
    title_suffix: str,
) -> Image.Image:
    """绘制 Market 赤毒/信条拍卖卡片。

    Args:
        renderer: CardRenderer 实例。
        data: MarketLichSister 模型。
        title_suffix: 标题后缀（"赤毒" 或 "信条"）。

    Returns:
        PIL Image 对象。
    """
    pay = data.payload
    if pay is None or not pay.auctions:
        return renderer.create_text_image(f"当前没有{title_suffix}拍卖数据", 800, 120)

    item_name = pay.item_name or "未知武器"
    auctions = pay.auctions
    content_h = _HEADER_H + len(auctions) * _ROW_H
    canvas_h = _TITLE_H + content_h + _FOOTER_H + 140

    title_font = FontManager.get_text_font(26)
    header_font = FontManager.get_text_font(18)
    row_font = FontManager.get_text_font(16)
    icon_font = FontManager.get_wf_icon_font(22)
    FontManager.get_text_font(16)

    cb = ImageCombiner(_CANVAS_W, canvas_h, ThemeColor.BG_DARK)
    cb.draw_double_border(12, ThemeColor.TABLE_BORDER, ThemeColor.DIVIDER, 2)

    current_y = _TITLE_H
    cb.set_color(ThemeColor.ACCENT_GOLD).set_font(title_font)
    cb.add_centered_text(f"{item_name} {title_suffix}拍卖信息", current_y)
    current_y += 30

    # --- 表头 / Table header ---
    header_text_y = current_y + _HEADER_H // 2 - 9
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(header_font)
    cb.add_text("元素", _MARGIN + _COL_ELEMENT_X, header_text_y)
    cb.add_text("伤害", _MARGIN + _COL_DAMAGE_X, header_text_y)
    cb.add_text("起拍价", _MARGIN + _COL_START_X, header_text_y)
    cb.add_text("买断价", _MARGIN + _COL_BUYOUT_X, header_text_y)
    cb.add_text("卖家", _MARGIN + _COL_SELLER_X, header_text_y)
    cb.add_text("声望", _MARGIN + _COL_REP_X, header_text_y)
    current_y += _HEADER_H + 5

    # --- 数据行 / Data rows ---
    for i, auction in enumerate(auctions):
        # 斑马条纹与文字共享相同的行区间，保证视觉居中。
        # Zebra stripe shares the same row span as text for true vertical centering.
        if i % 2 == 1:
            cb.set_color(ThemeColor.BG_CARD_ALT)
            cb.fill_rect(_MARGIN, current_y, _CANVAS_W - 2 * _MARGIN, _ROW_H)

        item = auction.item
        element_key = item.element if item else None
        element_name, element_color, element_icon = _resolve_element(element_key)
        damage = str(item.damage) if item and item.damage is not None else _UNKNOWN_LABEL
        starting = str(auction.starting_price) if auction.starting_price is not None else "无"
        buyout = str(auction.buyout_price) if auction.buyout_price is not None else "无"
        seller = _UNKNOWN_LABEL
        reputation = _UNKNOWN_LABEL
        if auction.owner is not None:
            seller = auction.owner.ingame_name or _UNKNOWN_LABEL
            seller = f"#{i + 1} {seller}"
            reputation = (
                str(auction.owner.reputation) if auction.owner.reputation is not None else _UNKNOWN_LABEL
            )

        text_y = current_y + _ROW_H // 2 - 8

        # 元素列：先绘制彩色图标（warframe_font_icon），再绘制中文名。
        # Element column: draw colored glyph icon first, then Chinese name.
        icon_x = _MARGIN + _COL_ELEMENT_X
        if element_icon:
            cb.set_color(element_color).set_font(icon_font)
            cb.add_text(element_icon, icon_x, text_y)
            icon_w = cb.get_string_width(element_icon)
            name_x = icon_x + icon_w + 6
        else:
            name_x = icon_x
        cb.set_color(element_color).set_font(row_font)
        cb.add_text(element_name, name_x, text_y)

        # 其他列 / Other columns
        cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(row_font)
        cb.add_text(damage, _MARGIN + _COL_DAMAGE_X, text_y)
        cb.add_text(starting, _MARGIN + _COL_START_X, text_y)
        cb.add_text(buyout, _MARGIN + _COL_BUYOUT_X, text_y)
        cb.add_text(seller, _MARGIN + _COL_SELLER_X, text_y)
        cb.add_text(reputation, _MARGIN + _COL_REP_X, text_y)

        current_y += _ROW_H

    # 私聊提示
    cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(FontManager.get_text_font(16))
    cb.add_centered_text(
        "回复 /w 序号 获取对应卖家的私聊语句（5 分钟内有效）",
        _TITLE_H + content_h + 30,
    )

    draw_standing(cb, max_w=310, max_h=420)
    cb.draw_card_footer(canvas_h, _FOOTER_H, 16)

    return cb.to_image()
