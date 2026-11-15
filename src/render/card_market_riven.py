"""Market 紫卡拍卖卡片

版式：页头（``紫卡市场 + 武器名``）+ 三列拍卖卡 + 私聊提示 + 看板娘 + 署名。

每张卡：

1. 序号 + 紫卡名（紫色），右上角 ``MR`` 与极性图标；
2. 分隔线 + 词条（元素词条带图标，正负用 ▲▼ 与红绿区分，最多 5 条）；
3. 分隔线 + 等级点 / 循环次数 / 直购标记（左）与买断价 + 白金图标（右）；
4. 起拍 / 最高（左）与卖家声望（右）；
5. 分隔线 + 卖家名与在线状态。

卡片高按「词条数」累加，同一行取较高者，底边对齐；宽夹在 400~490（三列放得下）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..wenum.element import ElementEnum
from ..wenum.icon import IconEnum
from . import card_frame as frame
from . import components as C
from .card_size import CardSpec, CustomBlock, measure_card_size
from .design import FONT, MAX_WIDTH, PAD, RADIUS, RGB, SPACE, font, semantic_color
from .theme import current_theme

if TYPE_CHECKING:
    from PIL import Image

    from ..model.market import MarketRiven, RivenAuction, RivenAttribute
    from .card_renderer import CardRenderer

#: 每行列数。
_COLUMNS = 3
#: 列间距 / 行间距。
_GAP = SPACE["lg"]
#: 卡片内边距。
_CARD_PAD = SPACE["lg"]
#: 卡片宽下限 / 上限。
_MIN_CARD_W = 400
_MAX_CARD_W = 490
#: 词条最多画几条（超出不画，避免卡片过高）。
_MAX_ATTRS = 5
#: 等级点总数。
_MAX_RANK = 8

#: 各段行高（绘制与测高共用）。
_DIVIDER_H = SPACE["sm"] + 1 + SPACE["sm"]
_ATTR_H = FONT["md"] + SPACE["xs"]
_PRICE_H = FONT["lg"] + SPACE["xs"]
_META_H = FONT["sm"] + SPACE["xs"]
_OWNER_H = FONT["md"] + SPACE["xs"]

#: 词条 url_name → 元素（这些词条显示元素图标与配色）。
_RIVEN_ELEMENT_MAP: dict[str, ElementEnum] = {
    "cold_damage": ElementEnum.COLD,
    "electric_damage": ElementEnum.ELECTRICITY,
    "toxin_damage": ElementEnum.TOXIN,
    "heat_damage": ElementEnum.HEAT,
    "impact_damage": ElementEnum.IMPACT,
    "puncture_damage": ElementEnum.PUNCTURE,
    "slash_damage": ElementEnum.SLASH,
}

#: 卖家状态 → 文案。
_STATUS_LABEL: dict[str, str] = {
    "online": "在线",
    "ingame": "游戏中",
    "offline": "离线",
    "invisible": "隐身",
}


@dataclass(frozen=True)
class _AttrLine:
    """一条紫卡词条的绘制文案。"""

    name: str
    value: str
    color: RGB
    icon: str
    arrow: str


@dataclass(frozen=True)
class _RivenCard:
    """一张拍卖卡的绘制文案。"""

    index: str
    name: str
    mastery: str
    polarity: str
    attrs: list[_AttrLine]
    dots: str
    re_rolls: str
    direct: bool
    buyout: str
    starting: str
    top_bid: str
    seller: str
    status: str
    status_color: RGB
    reputation: str
    height: int


def _resolve_attribute(attr: RivenAttribute, theme) -> _AttrLine:
    """词条 → (名称, 数值文本, 颜色, 图标, 箭头)。"""
    palette = theme.palette
    positive = bool(attr.positive)
    value = attr.value if attr.value is not None else 0.0
    value_text = f"{'+' if value >= 0 else ''}{value:.1f}%"

    element = _RIVEN_ELEMENT_MAP.get((attr.url_name or "").lower())
    if element is not None:
        return _AttrLine(
            name=f"{element.display_name}伤害",
            value=value_text,
            color=semantic_color(element.color, theme, palette.text_muted),
            icon=element.icon,
            arrow="",
        )
    return _AttrLine(
        name=attr.url_name or "未知词条",
        value=value_text,
        color=palette.green if positive else palette.red,
        icon="",
        arrow="▲" if positive else "▼",
    )


def _format_dots(rank: int | None, max_rank: int = _MAX_RANK) -> str:
    """mod 等级 → 实心/空心点。"""
    filled = min(max(rank or 0, 0), max_rank)
    return "●" * filled + "○" * (max_rank - filled)


def _build_card(
    auction: RivenAuction,
    index: int,
    theme,
) -> _RivenCard | None:
    """把一条拍卖转成绘制文案；``item`` 缺失时返回 ``None``。"""
    item = auction.item
    if item is None:
        return None

    palette = theme.palette
    attrs = [_resolve_attribute(attr, theme) for attr in (item.attributes or [])][:_MAX_ATTRS]

    starting = f"起拍 {auction.starting_price}" if auction.starting_price is not None else ""
    top_bid = f"最高 {auction.top_bid}" if auction.top_bid is not None else ""
    owner = auction.owner
    seller = (owner.ingame_name if owner and owner.ingame_name else "未知卖家")
    status = (owner.status if owner and owner.status else "")
    reputation = (
        f"声望 {owner.reputation}" if owner and owner.reputation is not None else ""
    )

    height = (
        _CARD_PAD * 2
        + FONT["md"]
        + _DIVIDER_H
        + len(attrs) * _ATTR_H
        + _DIVIDER_H
        + _PRICE_H
        + _META_H
        + _DIVIDER_H
        + _OWNER_H
    )

    return _RivenCard(
        index=f"#{index}",
        name=item.name or "未命名紫卡",
        mastery=f"MR{item.mastery_level}" if item.mastery_level is not None else "",
        polarity=item.polarity.icon if item.polarity is not None else "",
        attrs=attrs,
        dots=_format_dots(item.mod_rank),
        re_rolls=f"循环 {item.re_rolls if item.re_rolls is not None else 0}",
        direct=bool(auction.is_direct_sell),
        buyout=str(auction.buyout_price) if auction.buyout_price is not None else "议价",
        starting=starting,
        top_bid=top_bid,
        seller=seller,
        status=_STATUS_LABEL.get(status.lower(), status),
        status_color=C.status_color(status, palette),
        reputation=reputation,
        height=height,
    )


def _card_width(card: _RivenCard, theme) -> int:
    """单张卡的自然宽度（不含内边距）。"""
    body = font("md")
    small = font("sm")
    icon_w = FONT["md"]

    header = C.measure(card.index, body) + SPACE["sm"] + C.measure(card.name, font("md", bold=True))
    right = C.measure(card.mastery, small) + (SPACE["md"] + icon_w if card.polarity else 0)
    width = header + SPACE["xl"] + right

    for attr in card.attrs:
        lead = icon_w if attr.icon else C.measure(attr.arrow, body)
        width = max(
            width,
            lead + SPACE["sm"] + C.measure(attr.value, body) + SPACE["sm"] + C.measure(attr.name, small),
        )

    price = C.measure(card.dots, body) + SPACE["sm"] + C.measure(card.re_rolls, small)
    if card.direct:
        price += SPACE["md"] + C.measure("直购", small)
    price += SPACE["3xl"] + C.measure(card.buyout, font("lg")) + SPACE["sm"] + FONT["lg"]
    width = max(width, price)

    meta = C.measure(card.starting, small) + SPACE["md"] + C.measure(card.top_bid, small)
    meta += SPACE["3xl"] + C.measure(card.reputation, small)
    width = max(width, meta)

    owner = C.measure(card.seller, body) + SPACE["md"] + C.measure(card.status, small)
    return max(width, owner)


def _draw_card(page, card: _RivenCard, x: int, y: int, width: int, height: int) -> None:
    """画一张紫卡拍卖卡。"""
    palette = page.palette
    cb = page.cb
    cb.draw_rounded_rect(
        x, y, width, height,
        radius=RADIUS["md"],
        fill=palette.surface_alt,
        outline=palette.border,
        stroke_width=1,
    )

    inner_x = x + _CARD_PAD
    inner_w = width - _CARD_PAD * 2
    inner_right = inner_x + inner_w
    body = font("md")
    small = font("sm")
    cursor = y + _CARD_PAD

    # ---- 标题行：序号 + 紫卡名（左）｜ MR + 极性（右）----
    cb.set_color(palette.gold).set_font(body)
    cb.add_text(card.index, inner_x, cursor)
    name_x = inner_x + C.measure(card.index, body) + SPACE["sm"]

    right_w = C.measure(card.mastery, small) + (SPACE["md"] + FONT["md"] if card.polarity else 0)
    name_font = font("md", bold=True)
    cb.set_color(palette.rarity_legendary).set_font(name_font)
    cb.add_text(
        C.fit_text(card.name, inner_right - name_x - right_w - SPACE["md"], name_font),
        name_x,
        cursor,
    )

    if card.polarity:
        cb.set_color(palette.text).set_font(C.icon_font(FONT["md"]))
        cb.add_text(card.polarity, inner_right - FONT["md"], cursor)
    if card.mastery:
        mastery_right = inner_right - (FONT["md"] + SPACE["md"] if card.polarity else 0)
        cb.set_color(palette.text_muted).set_font(small)
        cb.add_text(
            card.mastery, mastery_right - C.measure(card.mastery, small), cursor + FONT["md"] - FONT["sm"]
        )
    cursor += FONT["md"]

    # ---- 分隔线 ----
    cursor += SPACE["sm"]
    cb.set_color(palette.border)
    cb.draw_line(inner_x, cursor, inner_right, cursor, width=1)
    cursor += 1 + SPACE["sm"]

    # ---- 词条 ----
    for attr in card.attrs:
        if attr.icon:
            cb.set_color(attr.color).set_font(C.icon_font(FONT["md"]))
            cb.add_text(attr.icon, inner_x, cursor)
            lead_w = FONT["md"]
        else:
            cb.set_color(attr.color).set_font(body)
            cb.add_text(attr.arrow, inner_x, cursor)
            lead_w = C.measure(attr.arrow, body)

        value_x = inner_x + lead_w + SPACE["sm"]
        cb.set_color(attr.color).set_font(body)
        cb.add_text(attr.value, value_x, cursor)

        name_x = value_x + C.measure(attr.value, body) + SPACE["sm"]
        cb.set_color(attr.color).set_font(small)
        cb.add_text(
            C.fit_text(attr.name, inner_right - name_x, small),
            name_x,
            cursor + FONT["md"] - FONT["sm"],
        )
        cursor += _ATTR_H

    # ---- 分隔线 ----
    cursor += SPACE["sm"]
    cb.set_color(palette.border)
    cb.draw_line(inner_x, cursor, inner_right, cursor, width=1)
    cursor += 1 + SPACE["sm"]

    # ---- 价格行：等级点 + 循环 + 直购（左）｜ 买断价 + 白金（右）----
    cb.set_color(palette.blue).set_font(body)
    cb.add_text(card.dots, inner_x, cursor)
    cursor_x = inner_x + C.measure(card.dots, body) + SPACE["sm"]
    cb.set_color(palette.text_muted).set_font(small)
    cb.add_text(card.re_rolls, cursor_x, cursor + FONT["md"] - FONT["sm"])
    cursor_x += C.measure(card.re_rolls, small) + SPACE["md"]
    if card.direct:
        cb.set_color(palette.green).set_font(small)
        cb.add_text("直购", cursor_x, cursor + FONT["md"] - FONT["sm"])

    price_font = font("lg")
    plat_w = FONT["lg"]
    price_w = C.measure(card.buyout, price_font)
    price_x = inner_right - price_w - SPACE["sm"] - plat_w
    cb.set_color(palette.gold).set_font(price_font)
    cb.add_text(card.buyout, price_x, cursor)
    cb.set_color(palette.icon_platinum).set_font(C.icon_font(FONT["lg"]))
    cb.add_text(IconEnum.PLATINUM.icon, inner_right - plat_w, cursor)
    cursor += _PRICE_H

    # ---- 起拍 / 最高（左）｜ 声望（右）----
    cb.set_color(palette.text_muted).set_font(small)
    if card.starting:
        cb.add_text(card.starting, inner_x, cursor)
    if card.top_bid:
        cb.add_text(
            card.top_bid, inner_x + C.measure(card.starting, small) + SPACE["md"], cursor
        )
    if card.reputation:
        cb.add_text(card.reputation, inner_right - C.measure(card.reputation, small), cursor)
    cursor += _META_H

    # ---- 分隔线 ----
    cursor += SPACE["sm"]
    cb.set_color(palette.border)
    cb.draw_line(inner_x, cursor, inner_right, cursor, width=1)
    cursor += 1 + SPACE["sm"]

    # ---- 卖家 + 状态 ----
    cb.set_color(palette.text).set_font(body)
    seller_text = C.fit_text(card.seller, inner_w - C.measure(card.status, small) - SPACE["md"], body)
    cb.add_text(seller_text, inner_x, cursor)
    if card.status:
        cb.set_color(card.status_color).set_font(small)
        cb.add_text(
            card.status,
            inner_x + C.measure(seller_text, body) + SPACE["md"],
            cursor + FONT["md"] - FONT["sm"],
        )


def render_market_riven_card(
    renderer: CardRenderer,
    market_riven: MarketRiven,
) -> Image.Image:
    """绘制 Market 紫卡市场卡片。

    Args:
        renderer: CardRenderer 实例（空数据时用它出提示图）。
        market_riven: MarketRiven 模型。

    Returns:
        PIL Image 对象。
    """
    payload = market_riven.payload
    if payload is None or not payload.auctions:
        return renderer.create_text_image("当前没有紫卡拍卖数据", 1040, 156)

    theme = current_theme()
    item_name = market_riven.item_name or "未知武器"

    cards: list[_RivenCard] = []
    for index, auction in enumerate(payload.auctions, 1):
        card = _build_card(auction, index, theme)
        if card is not None:  # item 缺失的条目不画，避免整张卡只剩边框
            cards.append(card)
    if not cards:
        return renderer.create_text_image("当前没有紫卡拍卖数据", 1040, 156)

    subtitle = f"{item_name} · 共 {len(cards)} 条在售"

    # ---- 卡片宽：最宽一张，夹在 [400, 490]（三列不能撑破画布）----
    max_card_w = (MAX_WIDTH - PAD * 2 - (_COLUMNS - 1) * _GAP) // _COLUMNS
    intrinsic = max(_card_width(card, theme) for card in cards)
    card_w = max(_MIN_CARD_W, min(_MAX_CARD_W, max_card_w, intrinsic + _CARD_PAD * 2))

    # 卡片少的时候不必占满三列（1~2 张就按实际张数排，画布更紧凑）
    columns = min(_COLUMNS, len(cards))
    row_heights = [
        max(card.height for card in cards[start : start + columns])
        for start in range(0, len(cards), columns)
    ]
    grid_w = card_w * columns + (columns - 1) * _GAP
    grid_h = sum(row_heights) + max(0, len(row_heights) - 1) * _GAP

    size = measure_card_size(
        CardSpec(
            title="Warframe Market 紫卡市场",
            subtitle=subtitle,
            blocks=[CustomBlock(width=grid_w, height=grid_h)],
            standing="md",
        )
    )

    page = C.new_page(theme, size.width, size.height)
    y = C.draw_header(page, "Warframe Market 紫卡市场", subtitle)

    grid_x = page.content_x + max(0, (page.content_w - grid_w) // 2)
    offset_y = 0
    for row_index, row_height in enumerate(row_heights):
        for column in range(columns):
            index = row_index * columns + column
            if index >= len(cards):
                break
            _draw_card(
                page,
                cards[index],
                grid_x + column * (card_w + _GAP),
                y + offset_y,
                card_w,
                row_height,
            )
        offset_y += row_height + _GAP

    frame.draw_standing_block(page, y + grid_h, "md")
    frame.draw_footer_block(page)
    return page.cb.to_image()
