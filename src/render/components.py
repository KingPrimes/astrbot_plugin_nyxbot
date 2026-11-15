"""Card components / 卡片组件

把「页面、页头、表格、徽标、提示、页脚」这些重复结构收成一组函数，
各 ``card_*.py`` 只负责准备数据，不再自己算坐标。

**宽度是量出来的，不是写死的**：卡片先调 ``measure_*`` 算出内容需要多宽，
再交给 ``design.resolve_width()`` 得到画布宽，最后 ``new_page()`` 建页。
所有绘制函数都接收 ``Page``，内部不出现全局画布常量。

所有尺寸与颜色都取自 ``design``，组件内部不出现裸 RGB 与魔法数字。
"""
from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

from astrbot.api import logger

from .design import (
    FONT,
    INNER_PAD,
    PAD,
    RADIUS,
    SPACE,
    Palette,
    RGB,
    Theme,
    font,
    icon_color,
    icon_font,
)
from .image_combiner import ImageCombiner
from .text_utils import get_text_width

# 离屏测量画布：只用来量字宽，与真正绘制共用同一套度量，避免量出来和画出来差几像素
_MEASURE_DRAW = ImageDraw.Draw(Image.new("RGB", (1, 1)))

FontLike = ImageFont.FreeTypeFont | ImageFont.ImageFont


def measure(text: str, text_font: FontLike) -> int:
    """文本像素宽（与 ``ImageCombiner.get_string_width`` 同源）。"""
    if not text:
        return 0
    return get_text_width(_MEASURE_DRAW, text, text_font)


# ---------------------------------------------------------------- 页面


@dataclass
class Page:
    """一张卡：画布 + 主题 + 内容区尺寸。

    ``width`` 由 ``design.resolve_width()`` 决定，``height`` 由调用方按内容算好。
    """

    theme: Theme
    width: int
    height: int
    cb: ImageCombiner

    @property
    def palette(self) -> Palette:
        """当前主题色板。"""
        return self.theme.palette

    @property
    def content_x(self) -> int:
        """内容区左边界。"""
        return PAD

    @property
    def content_y(self) -> int:
        """内容区上边界（卡面内边距之后）。"""
        return PAD + INNER_PAD

    @property
    def content_w(self) -> int:
        """内容区宽度。"""
        return self.width - PAD * 2

    def save(self, path) -> None:
        """保存为图片。"""
        self.cb.to_image().save(path)


def new_page(theme: Theme, width: int, height: int) -> Page:
    """创建画布并画出卡面（圆角 + 1px 边框）。"""
    cb = ImageCombiner(width, height, theme.palette.canvas)
    cb.draw_rounded_rect(
        PAD // 2,
        PAD // 2,
        width - PAD,
        height - PAD,
        radius=RADIUS["lg"],
        fill=theme.palette.surface,
        outline=theme.palette.border,
        stroke_width=1,
    )
    return Page(theme, width, height, cb)


def content_top() -> int:
    """内容区上边界。建页**之前**算高度时用（建页后用 ``page.content_y``）。"""
    return PAD + INNER_PAD


def content_left() -> int:
    """内容区左边界。建页**之前**算宽度时用（建页后用 ``page.content_x``）。"""
    return PAD


def footer_space() -> int:
    """内容底部到画布底部的留白（页脚高度 + 呼吸）。"""
    return PAD + FONT["sm"] + SPACE["sm"] + SPACE["xl"]


# ---------------------------------------------------------------- 测量


def measure_header(title: str, subtitle: str = "") -> int:
    """页头所需的最小内容宽度（标题 + 间距 + 副标题）。"""
    width = measure(title, font("2xl", bold=True))
    if subtitle:
        width += SPACE["3xl"] + measure(subtitle, font("base"))
    return width


def measure_column(index: int, column: Column, rows: list[list[tuple]]) -> int:
    """单列的自然宽度：表头 / 最宽单元格（含图标）取大，再加左右内边距。

    容错约定（与 :func:`draw_table` 一致）：行比列短时跳过缺失的单元格
    （``index >= len(row)`` 不参与测量），不视为错误——测量与绘制两侧
    对「行不完整」的假设必须相同。
    """
    cell_font = font("md", bold=True) if column.bold else font("md")
    widest = measure(column.title, font("base"))
    for row in rows:
        if index >= len(row):
            continue
        cell = row[index]
        cell_width = measure(cell[0] or "", cell_font)
        if len(cell) > 2 and cell[2]:
            cell_width += FONT["md"] + SPACE["xs"]
        widest = max(widest, cell_width)
    return max(column.min_width, widest + SPACE["md"] * 2)


def measure_table(columns: list[Column], rows: list[list[tuple]]) -> int:
    """表格铺满所需的最小内容宽度（各列自然宽度之和）。"""
    return sum(measure_column(index, column, rows) for index, column in enumerate(columns))


def distribute_columns(
    columns: list[Column],
    rows: list[list[tuple]],
    content_w: int,
) -> list[int]:
    """把 ``content_w`` 分给各列：先给足自然宽度，富余部分按 ``weight`` 摊。

    这样在自然宽度下不会有任何一列被压到截断；只有内容超过 ``MAX_WIDTH``
    （空间小于自然宽度之和）时才会等比压缩。
    """
    natural = [measure_column(index, column, rows) for index, column in enumerate(columns)]
    total_natural = sum(natural)

    if total_natural >= content_w:
        # 空间不够：按自然宽度等比压缩，最后一列吃掉取整误差
        widths = [max(1, natural[0] * content_w // total_natural)]
        for value in natural[1:]:
            widths.append(max(1, value * content_w // total_natural))
        widths[-1] += content_w - sum(widths)
        return widths

    # 空间富余：多出来的按权重分配
    surplus = content_w - total_natural
    total_weight = sum(column.weight for column in columns) or 1.0
    widths = [
        value + int(surplus * column.weight / total_weight)
        for value, column in zip(natural, columns, strict=True)
    ]
    widths[-1] += content_w - sum(widths)
    return widths


def measure_text_block(text: str, text_font: FontLike) -> int:
    """单行文本的宽度，等价于 ``measure``，供卡片直接调用时语义更清楚。"""
    return measure(text, text_font)


# ---------------------------------------------------------------- 文本


def fit_text(text: str, max_width: int, text_font: FontLike) -> str:
    """超出宽度时截断并加省略号（按实际字宽计算，中文安全）。"""
    if not text:
        return ""
    if measure(text, text_font) <= max_width:
        return text
    ellipsis = "…"
    limit = max_width - measure(ellipsis, text_font)
    out = ""
    for char in text:
        if measure(out + char, text_font) > limit:
            break
        out += char
    return out + ellipsis


def wrap_lines(
    text: str,
    max_width: int,
    text_font: FontLike,
    max_lines: int = 2,
    indent: int = 0,
) -> list[str]:
    """按宽度换行，超出 ``max_lines`` 时最后一行加省略号。

    优先在空格处断行（英文单词不会被拦腰截断），单个词超宽时才退化为逐字断行。

    Args:
        indent: 续行左侧留白（像素）。调用方绘制续行时需同步偏移，
            这样第二行与第一行的正文对齐，而不是对齐到 ``·`` 号。
    """
    if not text:
        return [""]

    lines: list[str] = []
    current = ""
    for word in text.split(" "):
        # 每行的可用宽度：首行满宽，续行扣掉缩进
        limit = max_width if not lines else max_width - indent
        candidate = f"{current} {word}".strip() if current else word
        if measure(candidate, text_font) <= limit:
            current = candidate
            continue

        if current:
            lines.append(current)
            current = ""
            limit = max_width - indent if lines else max_width

        if measure(word, text_font) <= limit:
            current = word
            continue

        # 单词本身超宽（中文长串）→ 逐字断行
        piece = ""
        for char in word:
            limit = max_width if not lines else max_width - indent
            if measure(piece + char, text_font) <= limit:
                piece += char
            else:
                lines.append(piece)
                piece = char
        current = piece

    if current:
        lines.append(current)

    if len(lines) <= max_lines:
        return lines

    head = lines[:max_lines]
    last_limit = max_width if max_lines <= 1 else max_width - indent
    head[-1] = fit_text(head[-1] + "…", last_limit, text_font)
    return head


def _align_x(text: str, x: int, width: int, align: str, text_font: FontLike) -> int:
    """按对齐方式算出文本左上角 x。"""
    if align == "left":
        return x
    text_w = measure(text, text_font)
    if align == "right":
        return x + width - text_w
    return x + (width - text_w) // 2


# ---------------------------------------------------------------- 页头


def draw_header(
    page: Page,
    title: str,
    subtitle: str = "",
    y: int | None = None,
) -> int:
    """页头：大标题 + 右侧副标题 + 分割线。

    Returns:
        分割线下方的内容起始 y。
    """
    palette = page.palette
    cb = page.cb
    top = page.content_y if y is None else y
    x = page.content_x

    title_font = font("2xl", bold=True)
    sub_font = font("base")
    sub_w = measure(subtitle, sub_font) if subtitle else 0
    title_text = fit_text(title, page.content_w - sub_w - SPACE["3xl"], title_font)
    cb.set_color(palette.text).set_font(title_font)
    cb.add_text(title_text, x, top)

    if subtitle:
        cb.set_color(palette.text_muted).set_font(sub_font)
        cb.add_text(subtitle, x + page.content_w - sub_w, top + FONT["2xl"] - FONT["base"] - 2)

    divider_y = top + FONT["2xl"] + SPACE["xl"]
    draw_divider(page, divider_y)
    return divider_y + SPACE["xl"]


def draw_divider(page: Page, y: int) -> None:
    """1px 分割线。"""
    page.cb.set_color(page.palette.border)
    page.cb.draw_line(page.content_x, y, page.content_x + page.content_w, y, width=1)


def draw_hint(page: Page, text: str, y: int) -> None:
    """居中提示（表格下方的操作说明）。"""
    hint_font = font("base")
    page.cb.set_color(page.palette.text_dim).set_font(hint_font)
    page.cb.add_centered_text(text, y)


def draw_footer(page: Page, text: str) -> None:
    """页脚署名。"""
    footer_font = font("sm")
    page.cb.set_color(page.palette.text_dim).set_font(footer_font)
    page.cb.add_centered_text(text, page.height - PAD - FONT["sm"] - SPACE["sm"])


# ---------------------------------------------------------------- 信息条


def measure_chips(chips: list[tuple]) -> int:
    """信息条所需的最小内容宽度。

    ``chips`` 每项是 ``(标签, 值)`` / ``(标签, 值, 图标)`` / ``(标签, 值, 图标, 图标色)``。
    """
    label_font = font("sm")
    value_font = font("md")
    width = 0
    shown = [chip for chip in chips if chip[1]]
    for chip in shown:
        width += measure(chip[0], label_font) + SPACE["sm"] + measure(chip[1], value_font)
        if len(chip) > 2 and chip[2]:
            width += FONT["md"] + SPACE["xs"]
    if shown:
        width += SPACE["3xl"] * (len(shown) - 1)
    return width


def draw_chips(page: Page, chips: list[tuple], y: int) -> int:
    """一行「标签 + 值（可带图标）」的小信息条，返回占用后的 y。

    Args:
        page: 页面。
        chips: ``(标签, 值)`` / ``(标签, 值, 图标)`` / ``(标签, 值, 图标, 图标色)``；
            图标为 Warframe 图标字体的字符，颜色省略时按图标语义取色。
        y: 顶部 y。
    """
    palette = page.palette
    cb = page.cb
    label_font = font("sm")
    value_font = font("md")
    icon_font_ = icon_font(FONT["md"])
    x = page.content_x
    height = FONT["md"] + SPACE["md"]

    for chip in chips:
        label, value = chip[0], chip[1]
        if not value:
            continue
        icon = chip[2] if len(chip) > 2 else None
        icon_tint = chip[3] if len(chip) > 3 else None

        cb.set_color(palette.text_dim).set_font(label_font)
        cb.add_text(label, x, y + 2)
        x += measure(label, label_font) + SPACE["sm"]

        if icon:
            cb.set_color(icon_tint or icon_color(icon, palette)).set_font(icon_font_)
            cb.add_text(icon, x, y)
            x += FONT["md"] + SPACE["xs"]

        cb.set_color(palette.text).set_font(value_font)
        cb.add_text(value, x, y)
        x += measure(value, value_font) + SPACE["3xl"]

    return y + height


# ---------------------------------------------------------------- 键值块


def measure_kv(rows: list[tuple], label_width: int = 0) -> int:
    """键值块所需的最小内容宽度（标签列 + 间距 + 值列）。

    ``rows`` 每项是 ``(标签, 值)`` 或 ``(标签, 值, 颜色)``，第三项不影响宽度。
    """
    label_font = font("sm")
    value_font = font("md")
    labels = label_width or max((measure(row[0], label_font) for row in rows), default=0)
    values = max((measure(row[1], value_font) for row in rows), default=0)
    return labels + SPACE["xl"] + values


def draw_kv(
    page: Page,
    rows: list[tuple],
    y: int,
    label_width: int = 0,
) -> int:
    """竖排「标签 + 值」，返回占用后的 y。

    Args:
        page: 页面。
        rows: ``(标签, 值)`` 或 ``(标签, 值, 颜色)`` 列表；颜色省略时用主文本色。
        y: 顶部 y。
        label_width: 标签列宽；0 表示按最长标签自适应（多张卡对齐时应显式传值）。
    """
    palette = page.palette
    cb = page.cb
    label_font = font("sm")
    value_font = font("md")
    if label_width == 0:
        label_width = max((measure(row[0], label_font) for row in rows), default=0)

    for row in rows:
        label, value = row[0], row[1]
        color = row[2] if len(row) > 2 and row[2] is not None else palette.text
        cb.set_color(palette.text_dim).set_font(label_font)
        cb.add_text(label, page.content_x, y + 2)
        cb.set_color(color).set_font(value_font)
        cb.add_text(value, page.content_x + label_width + SPACE["xl"], y)
        y += FONT["md"] + SPACE["md"]
    return y


# ---------------------------------------------------------------- 表格


@dataclass(frozen=True)
class Column:
    """表格列定义。"""

    title: str
    weight: float
    align: str = "left"
    min_width: int = 60
    bold: bool = False


def table_height(row_count: int) -> int:
    """表格总高（表头 + 行），建页前算高度用。"""
    header_h = FONT["base"] + SPACE["xl"]
    row_h = FONT["md"] + SPACE["2xl"] + SPACE["xs"]
    return header_h + SPACE["xs"] + max(0, row_count) * row_h


def draw_table(
    page: Page,
    columns: list[Column],
    rows: list[list[tuple]],
    y: int,
    x: int | None = None,
    width: int | None = None,
) -> int:
    """绘制表格（表头 + 斑马纹行）。

    Args:
        page: 页面。
        columns: 列定义，宽度按 weight 分配。
        rows: 每行是 ``(文本, 颜色)`` / ``(文本, 颜色, 图标字符)`` /
            ``(文本, 颜色, 图标字符, 图标颜色)``；颜色为 None 时用主文本色。
        y: 表格顶部 y。
        x: 表格左边界，默认内容区左边（用于并排双表）。
        width: 表格宽度，默认内容区宽。

    Returns:
        表格底部 y。

    容错约定（与 :func:`measure_column` 一致）：数据来自游戏 API，
    字段随时可能缺失——行比列短时只画已有的单元格（缺列留空），
    行比列长时多出的单元格忽略；两种情况记一条 warning，但**不抛异常**，
    不让一张卡因为少一个单元格而整卡崩溃。
    """
    palette = page.palette
    cb = page.cb
    content_w = width if width is not None else page.content_w
    x0 = x if x is not None else page.content_x
    widths = distribute_columns(columns, rows, content_w)

    header_h = FONT["base"] + SPACE["xl"]
    row_h = FONT["md"] + SPACE["2xl"] + SPACE["xs"]
    header_font = font("base")
    row_font = font("md")

    # 行列数不匹配只记一次日志（数据来自上游，渲染不能因此中断）
    mismatched = sum(1 for row in rows if len(row) != len(columns))
    if mismatched:
        logger.warning(
            f"draw_table 行列数不匹配（{mismatched}/{len(rows)} 行），"
            "缺失单元格留空、多余单元格忽略"
        )

    # 表头
    cb.set_color(palette.surface_alt)
    cb.draw_rounded_rect(x0, y, content_w, header_h, radius=RADIUS["sm"], fill=palette.surface_alt)
    cb.set_color(palette.text_muted).set_font(header_font)
    x = x0
    for col, width in zip(columns, widths, strict=True):
        text = fit_text(col.title, width - SPACE["lg"], header_font)
        cb.add_text(
            text,
            _align_x(text, x + SPACE["md"], width - SPACE["md"] * 2, col.align, header_font),
            y + (header_h - FONT["base"]) // 2,
        )
        x += width

    y += header_h + SPACE["xs"]

    # 数据行
    for index, row in enumerate(rows):
        if index % 2 == 1:
            cb.set_color(palette.surface_alt)
            cb.draw_rounded_rect(
                x0, y, content_w, row_h, radius=RADIUS["sm"], fill=palette.surface_alt
            )
        cb.set_font(row_font)
        x = x0
        for cell, col, width in zip(row, columns, widths):
            text, color = cell[0], cell[1]
            icon = cell[2] if len(cell) > 2 else None
            icon_tint = cell[3] if len(cell) > 3 else None
            cell_w = width - SPACE["md"] * 2
            cell_font = font("md", bold=True) if col.bold else row_font
            icon_w = FONT["md"] + SPACE["xs"] if icon else 0
            shown = fit_text(text, cell_w - icon_w, cell_font)
            group_w = measure(shown, cell_font) + icon_w

            if col.align == "right":
                start_x = x + width - SPACE["md"] - group_w
            elif col.align == "center":
                start_x = x + (width - group_w) // 2
            else:
                start_x = x + SPACE["md"]

            if icon:
                cb.set_color(icon_tint or icon_color(icon, palette)).set_font(
                    icon_font(FONT["md"])
                )
                cb.add_text(icon, start_x, y + (row_h - FONT["md"]) // 2)
                start_x += icon_w

            cb.set_color(color or palette.text).set_font(cell_font)
            cb.add_text(shown, start_x, y + (row_h - FONT["md"]) // 2)
            x += width
        y += row_h

    return y


# ---------------------------------------------------------------- 卖家状态

#: 卖家在线状态 → 调色板字段（market 系列卡片共用）。
_STATUS_FIELDS: dict[str, str] = {
    "online": "green",
    "ingame": "blue",
    "offline": "text_muted",
    "invisible": "text_dim",
}


def status_color(status: str, palette: Palette) -> RGB:
    """卖家在线状态 → 颜色（在线绿 / 游戏中蓝 / 隐身暗 / 其余次要色）。"""
    return getattr(palette, _STATUS_FIELDS.get((status or "").lower(), "text_muted"))


# ---------------------------------------------------------------- 稀有度


RARITY_ORDER: dict[str, int] = {
    "COMMON": 0,
    "UNCOMMON": 1,
    "RARE": 2,
    "LEGENDARY": 3,
}


def rarity_rank(value: str | None) -> int:
    """稀有度排序键：COMMON < UNCOMMON < RARE < LEGENDARY，未知值按常见处理。"""
    return RARITY_ORDER.get((value or "").upper(), 0)


def split_rarity_columns(
    items: list, rarity=lambda item: None  # noqa: ANN001
) -> tuple[list, list]:
    """把奖励拆成两列：左列全常见，右列罕见在上、稀有在下。

    Args:
        items: 奖励列表。
        rarity: 从元素取稀有度字符串的函数。

    Returns:
        ``(左列, 右列)``，两列长度可以不等。

    Note:
        右列为空（全是常见）或左列明显比右列长时，退化为「排序后左右均分」，
        避免出现一条极长、一条空着的单列。
    """
    ranked = sorted(items, key=lambda item: rarity_rank(rarity(item)))
    left = [item for item in ranked if rarity_rank(rarity(item)) == 0]
    right = [item for item in ranked if rarity_rank(rarity(item)) > 0]
    if not right or len(left) > len(right) + 1:
        half = (len(ranked) + 1) // 2
        return ranked[:half], ranked[half:]
    return left, right


# ---------------------------------------------------------------- 卡片网格


def draw_grid_card(
    page: Page,
    x: int,
    y: int,
    width: int,
    height: int,
    index: int | None = None,
) -> None:
    """网格卡的底（圆角 + 边框 + 右上角序号）。"""
    palette = page.palette
    cb = page.cb
    cb.draw_rounded_rect(
        x, y, width, height,
        radius=RADIUS["md"],
        fill=palette.surface_alt,
        outline=palette.border,
        stroke_width=1,
    )
    if index is not None:
        badge_font = font("xs")
        text = f"{index:02d}"
        cb.set_color(palette.gold).set_font(badge_font)
        cb.add_text(text, x + width - SPACE["md"] - measure(text, badge_font), y + SPACE["sm"])
