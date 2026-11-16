"""紫卡分析卡片渲染器

版式：页头（``紫卡分析趋势``）+ 三列分析卡 + 看板娘 + 署名。

每张卡（对应一把候选武器）：

1. 武器名（金色加粗）+ ``紫卡: xxx``（紫色后缀）；
2. 分隔线 + ``倾向点 / 倾向数值``（同行左右）+ ``武器类型``；
3. 分隔线 + 词条逐条，每条两行：
   - 第一行 ``词条名``（左） + ``本张卡的数值``（右，加粗）：百分比词条 ``+342.1%``、
     歧视词条 ``x1.06``、平值词条（穿透 / 攻击范围 / 连击持续时间 / 初始连击）``+3.5``；
   - 第二行 ``理论区间``（左，弱化，单位与数值一致）
     + ``| 差异``（右，负向红、正向绿；歧视词条同样是倍率，如 ``-0.09x``）。

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
#: 单条词条两行（实际数值 / 区间 + 差异）合计高度。
_ATTR_H = FONT["sm"] + SPACE["xs"] + FONT["sm"]
#: 分隔线占位（线 + 上下呼吸）。
_DIVIDER_H = SPACE["sm"] * 2 + 1


@dataclass(frozen=True)
class _AttrRow:
    """一条词条的绘制文案。

    第一行是「词条名 + 本张紫卡的实际数值」，第二行是「理论区间 + 与中位数的差异」：
    玩家最关心的是自己这张卡到底出了多少，原来只给区间和差异，等于看不到原值。
    """

    name: str
    value: str
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


def _format_float(value: float, digits: int = 1) -> str:
    """按固定小数位四舍五入（wiki 区间表是 0.1 精度：``220.5% - 269.5%``）。

    不做「去尾零」处理：``-99.0`` 去掉会变成 ``-99``，和同列的 ``151.9``
    位数不一致，读起来更乱。
    """
    return f"{round(value, digits):.{digits}f}"


def _signed(value: float) -> str:
    """平值词条的带符号文本：``+3.5`` / ``-0.4``（不带 %）。"""
    text = _format_float(abs(value))
    return f"+{text}" if value >= 0 else f"-{text}"


def _format_roll(attr) -> tuple[str, str]:
    """词条的实际数值与理论区间。

    三种单位各按卡面走：

    * 歧视词条 ``x1.06`` → 数值与区间都是倍率（``x1.46 - x1.56``）；
    * 平值词条（穿透 / 攻击范围 / 连击持续时间 / 初始连击 / 格挡角度）→ 数字本身，不带 %；
    * 其余百分比词条 → ``+342.1%`` / ``(293.5% - 358.7%)``。

    区间数据缺失时给「未知」，不要印一个 ``0% - 0%`` 假装算过。
    """
    if attr.discrimination:
        value = f"x{attr.attr:.2f}"
        span = f"(x{1 + attr.low / 100:.2f} - x{1 + attr.high / 100:.2f})"
    elif attr.flat:
        value = _signed(attr.attr)
        span = f"({_format_float(attr.low, 2)} - {_format_float(attr.high, 2)})"
    else:
        value = f"{attr.attr:+.1f}%"
        span = f"({_format_float(attr.low)}% - {_format_float(attr.high)}%)"
    if attr.low == 0 and attr.high == 0:
        span = "(区间未知)"
    return value, span


def _build_card(result: RivenAnalyseResult, palette) -> _AnalyseCard:
    """把一条分析结果转成绘制文案。"""
    attrs: list[_AttrRow] = []
    for attr in result.attributes or []:
        value, span = _format_roll(attr)
        known = not (attr.low == 0 and attr.high == 0)
        diff = f"| {attr.diff}" if known else ""
        attrs.append(
            _AttrRow(
                name=attr.attribute_name,
                value=value,
                span=span,
                diff=diff,
                color=palette.red if "-" in diff else palette.green,
            )
        )

    height = (
        _CARD_PAD * 2
        + FONT["md"]
        + (FONT["sm"] + SPACE["xs"] if result.riven_name else 0)
        + _DIVIDER_H
        + FONT["sm"] + SPACE["xs"]
        + FONT["sm"] + SPACE["sm"]
        + _DIVIDER_H
        + len(attrs) * (_ATTR_H + SPACE["md"])
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
    bold_font = font("sm", bold=True)
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
        width = max(
            width,
            C.measure(attr.name, small_font) + SPACE["xl"] + C.measure(attr.value, bold_font),
            C.measure(attr.span, tiny_font) + SPACE["xl"] + C.measure(attr.diff, small_font),
        )
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
    bold_font = font("sm", bold=True)
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

    # 词条：第一行「名称 + 实际数值」，第二行「理论区间 + 差异」
    for attr in card.attrs:
        value_w = C.measure(attr.value, bold_font)
        cb.set_color(palette.text).set_font(small_font)
        cb.add_text(
            C.fit_text(attr.name, inner_w - value_w - SPACE["md"], small_font),
            inner_x,
            cursor,
        )

        cb.set_color(palette.text).set_font(bold_font)
        cb.add_text(attr.value, inner_right - value_w, cursor)

        line2 = cursor + FONT["sm"] + SPACE["xs"]
        cb.set_color(palette.text_muted).set_font(tiny_font)
        cb.add_text(attr.span, inner_x, line2)

        cb.set_color(attr.color).set_font(small_font)
        if attr.diff:
            cb.add_text(
                attr.diff,
                inner_right - C.measure(attr.diff, small_font),
                line2 - (FONT["sm"] - FONT["xs"]),
            )
        cursor += _ATTR_H + SPACE["md"]


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

