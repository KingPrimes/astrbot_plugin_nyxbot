"""紫卡分析卡片渲染器

版式：页头（``紫卡分析趋势``）+ 三列分析卡 + 看板娘 + 署名。

每张卡（对应一把候选武器）：

1. 武器名（金色加粗）+ ``紫卡: xxx``（紫色后缀）；
2. 分隔线 + ``倾向点 / 倾向数值``（同行左右）+ ``武器类型``；
3. 分隔线 + 词条逐条：左侧名称，右侧 ``(最低% - 最高%)`` 与 ``| 差异``（负向红、正向绿）。

卡片高度按词条数实时累加，同一行的卡片取较高者，底边对齐。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import card_frame as frame
from . import components as C
from .card_size import CardSpec, CustomBlock, measure_card_size
from .design import FONT, MAX_WIDTH, PAD, RADIUS, RGB, SPACE, font
from .theme import current_theme

if TYPE_CHECKING:
    from PIL import Image

    from ..service.riven_analyse import RivenAnalyseResult
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
#: 单条词条的两行（区间 + 差异）合计高度。
_ATTR_H = FONT["xs"] + SPACE["xs"] + FONT["sm"]
#: 分隔线占位（线 + 上下呼吸）。
_DIVIDER_H = SPACE["sm"] * 2 + 1


@dataclass(frozen=True)
class _AttrRow:
    """一条词条的绘制文案。"""

    name: str
    span: str
    diff: str
    color: RGB


@dataclass(frozen=True)
class _AnalyseCard:
    """一张分析卡的绘制文案。"""

    weapon: str
    suffix: str
    dot: str
    omega: str
    weapon_type: str
    attrs: list[_AttrRow]
    height: int


def _format_float(value: float) -> str:
    """保留必要的小数位：整数补一位小数，其余最多 4 位有效数字。"""
    return f"{value:.1f}" if value == int(value) else f"{value:.4g}"


def _build_card(result: RivenAnalyseResult, palette) -> _AnalyseCard:
    """把一条分析结果转成绘制文案。"""
    attrs = [
        _AttrRow(
            name=attr.attribute_name,
            span=f"({_format_float(attr.low)}% - {_format_float(attr.high)}%)",
            diff=f"| {attr.diff}",
            color=palette.red if "-" in attr.diff else palette.green,
        )
        for attr in result.attributes or []
    ]

    height = (
        _CARD_PAD * 2
        + FONT["md"]
        + (FONT["sm"] + SPACE["xs"] if result.riven_name else 0)
        + _DIVIDER_H
        + FONT["sm"] + SPACE["xs"]
        + FONT["sm"] + SPACE["sm"]
        + _DIVIDER_H
        + len(attrs) * (_ATTR_H + SPACE["xs"])
    )
    return _AnalyseCard(
        weapon=result.weapon_name,
        suffix=f"紫卡: {result.riven_name}" if result.riven_name else "",
        dot=f"倾向点: {result.dot}",
        omega=f"倾向数值: {result.omega:.2f}",
        weapon_type=f"武器类型: {result.weapon_type}",
        attrs=attrs,
        height=height,
    )


def _row_width(card: _AnalyseCard, theme) -> int:
    """单张卡的自然宽度（不含内边距）。"""
    name_font = font("md", bold=True)
    small_font = font("sm")
    tiny_font = font("xs")

    width = C.measure(card.weapon, name_font)
    if card.suffix:
        width = max(width, C.measure(card.suffix, small_font))
    width = max(
        width,
        C.measure(card.dot, small_font) + SPACE["3xl"] + C.measure(card.omega, small_font),
        C.measure(card.weapon_type, small_font),
    )
    for attr in card.attrs:
        right = max(C.measure(attr.span, tiny_font), C.measure(attr.diff, small_font))
        width = max(width, C.measure(attr.name, small_font) + SPACE["xl"] + right)
    return width


def _draw_card(page, card: _AnalyseCard, x: int, y: int, width: int, height: int) -> None:
    """画一张紫卡分析卡。"""
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
    name_font = font("md", bold=True)
    small_font = font("sm")
    tiny_font = font("xs")
    cursor = y + _CARD_PAD

    # 武器名 + 紫卡后缀
    cb.set_color(palette.gold).set_font(name_font)
    cb.add_text(C.fit_text(card.weapon, inner_w, name_font), inner_x, cursor)
    cursor += FONT["md"]
    if card.suffix:
        cb.set_color(palette.rarity_legendary).set_font(small_font)
        cb.add_text(
            C.fit_text(card.suffix, inner_w, small_font), inner_x, cursor + SPACE["xs"] // 2
        )
        cursor += FONT["sm"] + SPACE["xs"]

    # 分隔线
    cursor += SPACE["sm"]
    cb.set_color(palette.border)
    cb.draw_line(inner_x, cursor, inner_right, cursor, width=1)
    cursor += 1 + SPACE["sm"]

    # 倾向点 / 倾向数值 / 武器类型
    cb.set_color(palette.text_muted).set_font(small_font)
    cb.add_text(card.dot, inner_x, cursor)
    cb.add_text(card.omega, inner_right - C.measure(card.omega, small_font), cursor)
    cursor += FONT["sm"] + SPACE["xs"]
    cb.add_text(
        C.fit_text(card.weapon_type, inner_w, small_font), inner_x, cursor
    )
    cursor += FONT["sm"] + SPACE["sm"]

    cb.set_color(palette.border)
    cb.draw_line(inner_x, cursor, inner_right, cursor, width=1)
    cursor += 1 + SPACE["sm"]

    # 词条
    for attr in card.attrs:
        right_w = max(C.measure(attr.span, tiny_font), C.measure(attr.diff, small_font))
        cb.set_color(palette.text).set_font(small_font)
        cb.add_text(
            C.fit_text(attr.name, inner_w - right_w - SPACE["md"], small_font),
            inner_x,
            cursor + FONT["xs"] - SPACE["xs"],
        )

        cb.set_color(palette.text_muted).set_font(tiny_font)
        cb.add_text(attr.span, inner_right - C.measure(attr.span, tiny_font), cursor)

        cb.set_color(attr.color).set_font(small_font)
        cb.add_text(
            attr.diff,
            inner_right - C.measure(attr.diff, small_font),
            cursor + FONT["xs"] + SPACE["xs"],
        )
        cursor += _ATTR_H + SPACE["xs"]


def render_riven_analyse_card(
    renderer: CardRenderer,
    results: list[RivenAnalyseResult],
) -> Image.Image:
    """绘制紫卡分析卡片。

    Args:
        renderer: CardRenderer 实例（空数据时用它出提示图）。
        results: 紫卡分析结果列表（每把候选武器一张卡）。

    Returns:
        PIL Image 对象。
    """
    if not results:
        return renderer.create_text_image("未识别到紫卡信息", 1040, 156)

    theme = current_theme()
    cards = [_build_card(result, theme.palette) for result in results]
    subtitle = f"共 {len(cards)} 把候选武器"

    # ---- 卡片宽：最宽一张，夹在 [400, 490]（三列不能撑破画布）----
    max_card_w = (MAX_WIDTH - PAD * 2 - (_COLUMNS - 1) * _GAP) // _COLUMNS
    intrinsic = max(_row_width(card, theme) for card in cards)
    card_w = max(_MIN_CARD_W, min(_MAX_CARD_W, max_card_w, intrinsic + _CARD_PAD * 2))

    # ---- 逐行取高，行内两卡等高 ----
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
            title="紫卡分析趋势",
            subtitle=subtitle,
            blocks=[CustomBlock(width=grid_w, height=grid_h)],
            standing="md",
        )
    )

    page = C.new_page(theme, size.width, size.height)
    y = C.draw_header(page, "紫卡分析趋势", subtitle)

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

