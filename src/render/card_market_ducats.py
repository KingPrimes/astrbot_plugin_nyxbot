"""Market 杜卡币卡片渲染器 — 迁移自 Java DefaultDrawMarketDucatsImage

版式：页头 + 左右并排两张表（当天 / 每小时）+ 看板娘 + 署名。
每张表 5 列：名称 / 杜卡币 / 杜卡币-白金 / 均价 / 库存；
行色按排名从「金/银」渐变到弱化色，与旧版一致。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from . import card_frame as frame
from . import components as C
from .card_size import CardSpec, CustomBlock, measure_card_size
from .design import FONT, SPACE, font
from .draw_constant import lerp_color
from .theme import current_theme

if TYPE_CHECKING:
    from PIL import Image

    from ..model.market import DucatItem
    from .card_renderer import CardRenderer

#: 双表并排时至少需要的宽度（两张表各约 320 + 间隙）。
MIN_TABLE_AREA_W = 650


def _fmt(value: float | None, digits: int = 2) -> str:
    return f"{value:.{digits}f}" if value is not None else "N/A"


def _row_values(item: DucatItem) -> list[str]:
    return [
        item.item_name or "未知物品",
        str(item.ducats) if item.ducats is not None else "N/A",
        _fmt(item.ducats_per_platinum_wa),
        _fmt(item.wa_price),
        str(item.volume) if item.volume is not None else "N/A",
    ]


def render_market_ducats_card(
    renderer: CardRenderer,
    day_items: list[DucatItem],
    hour_items: list[DucatItem],
    title: str,
) -> Image.Image:
    """绘制 Market 杜卡币卡片 — 镜像 Java drawMarketDucatsImage()。

    Args:
        renderer: CardRenderer 实例（保留参数以兼容渲染入口）。
        day_items: 当天数据列表。
        hour_items: 每小时数据列表。
        title: 标题（"金垃圾" 或 "银垃圾"）。
    """
    if not day_items and not hour_items:
        return renderer.create_text_image(f"当前没有{title}数据", 800, 120)

    theme = current_theme()
    palette = theme.palette

    columns = [
        C.Column("名称", 2.4, "left", 120),
        C.Column("杜卡币", 1.0, "right", 80),
        C.Column("杜卡币/白金", 1.4, "right", 100),
        C.Column("均价", 1.0, "right", 80),
        C.Column("库存", 0.9, "right", 70),
    ]

    rank_start = palette.gold if "金" in title else palette.rarity_uncommon

    def build_rows(items: list[DucatItem]) -> list[list[tuple]]:
        total = max(len(items), 1)
        rows: list[list[tuple]] = []
        for index, item in enumerate(items):
            # 排名渐变：整行统一颜色，越靠后越弱化
            t = index / max(total - 1, 1)
            color = lerp_color(rank_start, palette.text_muted, t)
            rows.append([(value, color) for value in _row_values(item)])
        return rows

    day_rows = build_rows(day_items)
    hour_rows = build_rows(hour_items)
    max_rows = max(len(day_rows), len(hour_rows), 1)

    # 审查 P2-9：左右双表用**合并数据**测一次，列宽向量共用，列边界才对齐
    combined_rows = day_rows + hour_rows
    natural = C.measure_table(columns, combined_rows)
    gap = SPACE["xl"]
    label_h = FONT["sm"] + SPACE["sm"]
    size = measure_card_size(
        CardSpec(
            title=title,
            blocks=[
                CustomBlock(
                    width=natural * 2 + gap,
                    height=label_h + C.table_height(max_rows),
                )
            ],
            standing="sm",
            extra_width=MIN_TABLE_AREA_W,
        )
    )

    content_w = size.content_width
    half_w = (content_w - gap) // 2
    right_x = C.content_left() + half_w + gap

    page = C.new_page(theme, size.width, size.height)
    y = C.draw_header(page, title)

    cb = page.cb
    cb.set_color(palette.text_muted).set_font(font("sm"))
    cb.add_text("当天", C.content_left(), y)
    cb.add_text("每小时", right_x, y)

    table_y = y + label_h
    shared_widths = C.distribute_columns(columns, combined_rows, half_w)
    left_bottom = C.draw_table(
        page, columns, day_rows, table_y, x=C.content_left(), width=half_w, widths=shared_widths
    )
    right_bottom = C.draw_table(
        page, columns, hour_rows, table_y, x=right_x, width=half_w, widths=shared_widths
    )

    frame.draw_standing_block(page, max(left_bottom, right_bottom), "sm")
    frame.draw_footer_block(page)
    return page.cb.to_image()
