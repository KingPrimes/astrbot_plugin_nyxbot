"""Market 赤毒/信条拍卖卡片

版式：页头（``武器 + 赤毒/信条拍卖``）+ 六列表格 + 私聊提示 + 看板娘 + 署名。

| 列 | 内容 |
|---|---|
| 元素 | ``ElementEnum`` 图标 + 中文名，按元素配色 |
| 伤害 / 起拍 / 买断 | 数值，售价列金色 |
| 卖家 | ``#序号 名称``（序号给 ``/w`` 用） |
| 声望 | 卖家声望，右对齐 |

宽度由表格自然宽与私聊提示取大，高度按行数累加，不再写死 1350×N。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..wenum.element import ElementEnum
from . import card_frame as frame
from . import components as C
from .card_size import CardSpec, TableBlock, TextBlock, measure_card_size
from .design import FONT, SPACE, semantic_color
from .theme import current_theme

if TYPE_CHECKING:
    from PIL import Image

    from ..model.market import MarketLichSister
    from .card_renderer import CardRenderer

#: 表格列定义（weight 决定富余宽度怎么分，min_width 保证不被压扁）。
_COLUMNS: tuple[C.Column, ...] = (
    C.Column("元素", 1.6, "left", 130),
    C.Column("伤害", 0.8, "left", 80),
    C.Column("起拍", 1.0, "right", 90),
    C.Column("买断", 1.0, "right", 90),
    C.Column("卖家", 2.2, "left", 180),
    C.Column("声望", 0.8, "right", 80),
)

_UNKNOWN = "未知"

#: 私聊提示（表格下方）。
WHISPER_HINT = "回复 /w 序号 获取对应卖家的私聊语句（2 分钟内有效）"


def _resolve_element(key: str | None, theme) -> tuple[str, tuple[int, int, int], str]:
    """元素 key → (中文名, 主题适配色, 图标字形)；未知 key 原样展示。"""
    palette = theme.palette
    if not key:
        return _UNKNOWN, palette.text_muted, ""
    try:
        member = ElementEnum[key.upper()]
    except KeyError:
        return key, palette.text_muted, ""
    return member.display_name, semantic_color(member.color, theme, palette.text_muted), member.icon


def _build_rows(auctions, theme) -> list[list[tuple]]:
    """拍卖列表 → 表格行。"""
    palette = theme.palette
    rows: list[list[tuple]] = []
    for index, auction in enumerate(auctions, 1):
        item = auction.item
        name, color, icon = _resolve_element(item.element if item else None, theme)
        damage = str(item.damage) if item and item.damage is not None else _UNKNOWN

        starting = str(auction.starting_price) if auction.starting_price is not None else "无"
        buyout = str(auction.buyout_price) if auction.buyout_price is not None else "无"

        seller = _UNKNOWN
        reputation = _UNKNOWN
        if auction.owner is not None:
            seller = f"#{index} {auction.owner.ingame_name or _UNKNOWN}"
            if auction.owner.reputation is not None:
                reputation = str(auction.owner.reputation)

        rows.append(
            [
                (name, color, icon, color),
                (damage, palette.text),
                (starting, palette.gold),
                (buyout, palette.gold),
                (seller, palette.text),
                (reputation, palette.text_muted),
            ]
        )
    return rows


def render_market_lich_sister_card(
    renderer: CardRenderer,
    data: MarketLichSister,
    title_suffix: str,
) -> Image.Image:
    """绘制 Market 赤毒/信条拍卖卡片。

    Args:
        renderer: CardRenderer 实例（空数据时用它出提示图）。
        data: MarketLichSister 模型。
        title_suffix: 标题后缀（"赤毒" 或 "信条"）。

    Returns:
        PIL Image 对象。
    """
    payload = data.payload
    if payload is None or not payload.auctions:
        return renderer.create_text_image(f"当前没有{title_suffix}拍卖数据", 800, 120)

    theme = current_theme()
    item_name = payload.item_name or "未知武器"
    rows = _build_rows(payload.auctions, theme)
    title = f"{item_name} {title_suffix}拍卖"
    subtitle = f"共 {len(rows)} 条在售"

    size = measure_card_size(
        CardSpec(
            title=title,
            subtitle=subtitle,
            blocks=[
                TableBlock(columns=_COLUMNS, rows=rows, gap=SPACE["lg"]),
                TextBlock(lines=[WHISPER_HINT], size="base"),
            ],
            standing="md",
        )
    )

    page = C.new_page(theme, size.width, size.height)
    y = C.draw_header(page, title, subtitle)
    table_bottom = C.draw_table(page, _COLUMNS, rows, y)

    hint_top = table_bottom + SPACE["lg"]
    C.draw_hint(page, WHISPER_HINT, hint_top)
    frame.draw_standing_block(page, hint_top + FONT["base"] + SPACE["xs"], "md")
    frame.draw_footer_block(page)
    return page.cb.to_image()
