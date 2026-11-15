"""帮助卡片渲染器 — 帮助内容的图片版式

平台不支持 Markdown（或用户关闭了「使用 Markdown 进行回复」）时，
帮助内容降级为这张卡；内容与 Markdown 版本同源（``src.help.catalog``），
因此两种发送方式信息完全一致。

版式：页头 + 按分节排列的「指令 / 说明」双列表格 + 看板娘 + 署名。
多节表格共用同一份列宽向量（先按合并数据量一次），列边界才能上下对齐。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..help.catalog import HELP_SUBTITLE, HELP_TITLE
from . import card_frame as frame
from . import components as C
from .card_size import CardSpec, CustomBlock, measure_card_size
from .design import FONT, SPACE, font
from .theme import current_theme

if TYPE_CHECKING:
    from PIL import Image

    from ..help.catalog import HelpSection
    from .card_renderer import CardRenderer

#: 标题取自内容目录（catalog 零依赖），避免两种发送方式各写一份标题。
TITLE = HELP_TITLE
SUBTITLE = HELP_SUBTITLE

#: 分节小标题占用的高度（字阶 + 与表格的间距）。
CAPTION_H = FONT["sm"] + SPACE["sm"]

#: 分节之间的间距。
SECTION_GAP = SPACE["2xl"]

#: 两列固定不变，模块级共享；列宽由内容量出后再分配。
COLUMNS: tuple[C.Column, ...] = (
    C.Column("指令", 1.0, "left", 140),
    C.Column("说明", 2.4, "left", 200),
)


def _section_rows(section: HelpSection, command_color: tuple[int, int, int]) -> list[list[tuple]]:
    """把一节帮助转成表格行 ``[(指令, 色), (说明, 主文本色)]``。"""
    if not section.entries:
        return [[("—", command_color), ("—", None)]]
    return [
        [(entry.usage, command_color), (entry.description, None)]
        for entry in section.entries
    ]


def render_help_card(
    renderer: CardRenderer,
    sections: tuple[HelpSection, ...] | list[HelpSection],
    title: str = TITLE,
    subtitle: str = SUBTITLE,
) -> Image.Image:
    """绘制帮助卡片 / Render the help card.

    Args:
        renderer: CardRenderer 实例（保留参数以兼容渲染入口）。
        sections: 帮助分节（:func:`src.help.catalog.build_help_sections`）。
        title: 卡片标题。
        subtitle: 页头右侧副标题。

    Returns:
        PIL Image 对象。
    """
    theme = current_theme()
    palette = theme.palette
    columns = list(COLUMNS)
    rows_by_section = [_section_rows(section, palette.gold) for section in sections]
    all_rows = [row for rows in rows_by_section for row in rows]

    # 合并所有行量一次，各节表列边界才能对齐（同 card_market_ducats 的双表处理）
    natural = C.measure_table(columns, all_rows)
    body_h = sum(
        CAPTION_H + C.table_height(len(rows)) for rows in rows_by_section
    ) + SECTION_GAP * max(0, len(rows_by_section) - 1)

    size = measure_card_size(
        CardSpec(
            title=title,
            subtitle=subtitle,
            blocks=[CustomBlock(width=natural, height=body_h)],
            standing="sm",
            header_gap=SPACE["md"],
        )
    )

    page = C.new_page(theme, size.width, size.height)
    y = C.draw_header(page, title, subtitle) + SPACE["md"]
    widths = C.distribute_columns(columns, all_rows, page.content_w)
    caption_font = font("sm", bold=True)

    for index, (section, rows) in enumerate(zip(sections, rows_by_section, strict=True)):
        if index:
            y += SECTION_GAP
        page.cb.set_color(palette.text_muted).set_font(caption_font)
        page.cb.add_text(section.title, C.content_left(), y)
        y = C.draw_table(page, columns, rows, y + CAPTION_H, widths=widths)

    frame.draw_standing_block(page, y, "sm")
    frame.draw_footer_block(page)
    return page.cb.to_image()
