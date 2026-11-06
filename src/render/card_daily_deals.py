"""每日特惠卡片渲染器

对应 Java DefaultDrawDailyDealsImage.java。
版式：页头 + 键值块（物品 / 原价现价 / 折扣 / 总数剩余 / 剩余时间）+ 看板娘 + 署名。

价格行保留原版的「原价红色 + 删除线、现价绿色」，其余走 ``components.draw_kv``。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from . import card_frame as frame
from . import components as C
from .card_size import CardSpec, CustomBlock, measure_card_size
from .design import FONT, SPACE, font
from .theme import current_theme

if TYPE_CHECKING:
    from PIL import Image

    from ..model.world_state import DailyDeals
    from .card_renderer import CardRenderer


def _draw_price_row(page, y: int, label_width: int, original: int, sale: int) -> int:
    """原价（红 + 删除线）/ 现价（绿）行。"""
    palette = page.palette
    cb = page.cb
    label_font = font("sm")
    value_font = font("md")
    value_x = page.content_x + label_width + SPACE["xl"]

    cb.set_color(palette.text_dim).set_font(label_font)
    cb.add_text("原价/现价", page.content_x, y + 2)

    original_text = str(original)
    cb.set_color(palette.red).set_font(value_font)
    cb.add_text(original_text, value_x, y)
    original_w = C.measure(original_text, value_font)
    cb.draw_line(value_x, y + FONT["md"] // 2 + 2, value_x + original_w, y + FONT["md"] // 2 + 2, width=2)

    cb.set_color(palette.text_muted).set_font(value_font)
    cb.add_text("/", value_x + original_w + SPACE["sm"], y)

    cb.set_color(palette.green).set_font(value_font)
    cb.add_text(str(sale), value_x + original_w + SPACE["sm"] * 3, y)

    return y + FONT["md"] + SPACE["md"]


def render_daily_deals_card(
    renderer: CardRenderer,
    deals: list[DailyDeals],
) -> Image.Image:
    """绘制每日特惠卡片 — 对应 Java drawDailyDealsImage()。

    Args:
        renderer: CardRenderer 实例（保留参数以兼容渲染入口）。
        deals: DailyDeals 模型列表（仅渲染第一个）。
    """
    if not deals:
        return renderer.create_text_image("当前没有每日特惠数据")

    theme = current_theme()
    palette = theme.palette
    deal = deals[0]

    original = deal.original_price or 0
    sale = deal.sale_price or 0
    total = deal.total or 0
    sold = deal.sold or 0
    remaining = total - sold

    label_width = max(
        C.measure(label, font("sm"))
        for label in ("物品名称", "原价/现价", "折扣比", "总/余", "剩余时间")
    )
    plain_rows: list[tuple] = [
        ("物品名称", deal.item or "未知物品"),
        ("折扣比", f"{deal.discount or 0:.0f}%", palette.red),
        ("总/余", f"{total} / {remaining}", palette.green),
        ("剩余时间", deal.time_left or "未知", palette.amber),
    ]

    body_h = 5 * (FONT["md"] + SPACE["md"])
    size = measure_card_size(
        CardSpec(
            title="每日特惠",
            blocks=[
                CustomBlock(width=C.measure_kv(plain_rows, label_width), height=body_h)
            ],
            standing="md",
            header_gap=SPACE["md"],
        )
    )

    page = C.new_page(theme, size.width, size.height)
    y = C.draw_header(page, "每日特惠") + SPACE["md"]
    y = C.draw_kv(page, [plain_rows[0]], y, label_width=label_width)
    y = _draw_price_row(page, y, label_width, original, sale)
    y = C.draw_kv(page, plain_rows[1:], y, label_width=label_width)
    frame.draw_standing_block(page, y, "md")
    frame.draw_footer_block(page)
    return page.cb.to_image()
