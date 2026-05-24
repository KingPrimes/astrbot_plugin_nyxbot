"""Market 紫卡卡片渲染器 — 迁移自 Java DefaultDrawMarketRivenImage

布局：
  - 4 列网格布局，每张卡片 632×800px（不含模板图片，使用暗色卡片背景）
  - 卡片内容: 武器名称 / 紫卡名称 / 属性词条 / 极性 / 段位 / 循环次数
  - 深色主题 + 看板娘立绘
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image

from .draw_constant import DrawConstant, ThemeColor
from .font_manager import FontManager
from .image_combiner import ImageCombiner
from .standing import draw_standing

if TYPE_CHECKING:
    from ..model.market import MarketRiven, RivenAuction
    from .card_renderer import CardRenderer

_CARD_W = 632
_CARD_H = 800
_CARD_MARGIN = 20
_COLUMNS = 4
_RIVEN_TEXT_COLOR = (134, 105, 167)  # #8669A7


def render_market_riven_card(
    renderer: CardRenderer,
    market_riven: MarketRiven,
) -> Image.Image:
    """绘制 Market 紫卡市场卡片 — 4 列网格布局。

    Args:
        renderer: CardRenderer 实例。
        market_riven: MarketRiven 模型。

    Returns:
        PIL Image 对象。
    """
    pay = market_riven.payload
    if pay is None or not pay.auctions:
        return renderer.create_text_image("当前没有紫卡拍卖数据", 800, 120)

    auctions = pay.auctions
    item_name = market_riven.item_name or "未知武器"

    rows = (len(auctions) + _COLUMNS - 1) // _COLUMNS
    total_w = _CARD_W * _COLUMNS + _CARD_MARGIN * (_COLUMNS + 1)
    total_h = _CARD_H * rows + _CARD_MARGIN * (rows + 1) + 200

    cb = ImageCombiner(total_w, total_h, ThemeColor.BG_DARK)
    cb.draw_double_border(12, ThemeColor.TABLE_BORDER, ThemeColor.DIVIDER, 2)

    # --- 标题 ---
    title_font = FontManager.get_text_font(42)
    cb.set_color(ThemeColor.ACCENT_GOLD).set_font(title_font)
    cb.add_centered_text("Warframe Market 紫卡市场", 60)

    # --- 卡片网格 ---
    card_start_y = 110
    for i, auction in enumerate(auctions):
        row = i // _COLUMNS
        col = i % _COLUMNS
        card_x = _CARD_MARGIN + col * (_CARD_W + _CARD_MARGIN)
        card_y = card_start_y + _CARD_MARGIN + row * (_CARD_H + _CARD_MARGIN)
        card_img = _draw_riven_card(item_name, auction)
        cb.draw_image(card_img, card_x, card_y)

    # --- 看板娘 ---
    draw_standing(cb, max_w=310, max_h=420)

    # --- 底部署名 ---
    footer_font = FontManager.get_text_font(18)
    cb.set_color(ThemeColor.TEXT_MUTED).set_font(footer_font)
    cb.add_centered_text(DrawConstant.FOOTER_TEXT, total_h - 40)

    return cb.to_image()


def _draw_riven_card(item_name: str, auction: RivenAuction) -> Image.Image:
    """绘制单张紫卡卡片。

    Args:
        item_name: 武器名称。
        auction: 紫卡拍卖数据。

    Returns:
        单张卡片的 PIL Image。
    """
    cb = ImageCombiner(_CARD_W, _CARD_H, ThemeColor.BG_CARD)

    rim = auction.item
    if rim is None:
        return cb.to_image()

    name_font = FontManager.get_text_font(26)
    attr_font = FontManager.get_text_font(22)
    small_font = FontManager.get_text_font(18)

    # 卡片边框
    cb.set_color(ThemeColor.TABLE_BORDER)
    cb.draw_line(0, 0, _CARD_W, 0, width=2)
    cb.draw_line(0, _CARD_H - 2, _CARD_W, _CARD_H - 2, width=2)
    cb.draw_line(0, 0, 0, _CARD_H, width=2)
    cb.draw_line(_CARD_W - 2, 0, _CARD_W - 2, _CARD_H, width=2)

    # 武器名称
    current_y = 30
    cb.set_color(ThemeColor.ACCENT_GOLD).set_font(name_font)
    cb.add_centered_text(item_name, current_y)
    current_y += 36

    # 紫卡名称
    cb.set_color(_RIVEN_TEXT_COLOR).set_font(name_font)
    if rim.name:
        cb.add_centered_text(rim.name, current_y)
    current_y += 80

    # 极性
    if rim.polarity:
        cb.set_color(_RIVEN_TEXT_COLOR).set_font(name_font)
        cb.add_text(f"极性: {rim.polarity}", 40, current_y)
        current_y += 36

    # 段位
    if rim.mastery_level is not None:
        cb.set_color(_RIVEN_TEXT_COLOR).set_font(name_font)
        cb.add_text(f"段位: {rim.mastery_level}", 40, current_y)
        current_y += 36

    # 词条
    if rim.attributes:
        current_y += 10
        cb.set_color(_RIVEN_TEXT_COLOR).set_font(attr_font)
        for attr in rim.attributes:
            val = attr.value if attr.value is not None else 0
            url_name = attr.url_name or "未知"
            text = f"{val:.1f}  {url_name}"
            cb.add_centered_text(text, current_y)
            current_y += 32

    # 底部分隔线
    bottom_y = _CARD_H - 130
    cb.set_color(ThemeColor.DIVIDER)
    cb.draw_line(40, bottom_y, _CARD_W - 40, bottom_y, width=1)

    # 卖家昵称
    if auction.owner and auction.owner.ingame_name:
        cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(name_font)
        cb.add_text(auction.owner.ingame_name, 40, bottom_y + 36)

    # 买断价格
    if auction.buyout_price is not None:
        cb.set_color(ThemeColor.ACCENT_GOLD).set_font(name_font)
        cb.add_text(f"{auction.buyout_price} plat", 40, bottom_y + 72)

    # MOD 等级（底部点）
    if rim.mod_rank is not None:
        cb.set_color(ThemeColor.CYCLE_COLD).set_font(small_font)
        dots = "●" * min(rim.mod_rank, 8)
        cb.add_text(dots, 40, _CARD_H - 36)

    # 循环次数
    if rim.re_rolls is not None:
        cb.set_color(_RIVEN_TEXT_COLOR).set_font(small_font)
        cb.add_text(f"循环: {rim.re_rolls}", _CARD_W - 140, _CARD_H - 36)

    return cb.to_image()
