"""虚空商人卡片渲染器 — 迁移自 Java DefaultDrawVoidTraderImage

版式：页头 + 信息条（位置 / 剩余时间）+ 商品表格（商品 / 杜卡币 / 星币）
+ 看板娘 + 署名。价格列用 icon_registry 的货币图标，颜色取调色板的货币身份色。

商品清单可能很长：画布高度有上限（``DEFAULT_MAX_HEIGHT``），放不下的行
**主动截断并附提示行**（审查 R8），不让商品悄悄画到画布外。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from . import card_frame as frame
from . import components as C
from .card_size import CardSpec, ChipsBlock, TableBlock, measure_card_size
from .design import SPACE
from .icon_registry import icon_char
from .theme import current_theme

if TYPE_CHECKING:
    from PIL import Image

    from ..model.world_state import VoidTrader
    from .card_renderer import CardRenderer


def _fit_rows(
    rows: list[list[tuple]],
    columns: list[C.Column],
    chips: list[tuple[str, str]],
    hidden_noun: str,
) -> list[list[tuple]]:
    """把表格行裁剪到画布高度上限内，被裁时附「还有 N 件未展示」提示行。

    用零行卡探测固定开销（页头 / 信息条 / 表头 / 看板娘 / 页脚），
    得出可容纳的行数预算——不写死行数上限，主题或档位变化自动跟随。
    """
    from .card_size import DEFAULT_MAX_HEIGHT

    probe = measure_card_size(
        CardSpec(
            title="虚空商人",
            blocks=[ChipsBlock(chips), TableBlock(columns=columns, rows=[])],
            standing="md",
        )
    )
    row_h = C.table_height(1) - C.table_height(0)
    max_rows = max(1, (DEFAULT_MAX_HEIGHT - probe.height) // row_h)
    if len(rows) <= max_rows:
        return rows

    hidden = len(rows) - (max_rows - 1)
    muted = current_theme().palette.text_dim
    hint_row = [
        (f"… 还有 {hidden} {hidden_noun}未展示", muted),
        ("", muted),
        ("", muted),
    ]
    return rows[: max_rows - 1] + [hint_row]


def _item_name(raw: str | None) -> str:
    """路径式物品名取最后一段，下划线换空格。"""
    text = raw or "未知物品"
    if "/" in text:
        text = text.rsplit("/", 1)[-1]
    return text.replace("_", " ")


def _credits_text(value: int) -> str:
    return f"{value / 1000:.0f}K" if value >= 1000 else str(value)


def render_void_trader_card(
    renderer: CardRenderer,
    trader: VoidTrader,
) -> Image.Image:
    """绘制虚空商人卡片 — 对应 Java drawVoidTraderImage()。

    Args:
        renderer: CardRenderer 实例（保留参数以兼容渲染入口）。
        trader: VoidTrader 模型。
    """
    theme = current_theme()
    palette = theme.palette

    location = trader.node or "未知位置"
    time_left = trader.time_left or "未知"

    columns = [
        C.Column("商品", 3.4, "left", 220),
        C.Column("杜卡币", 1.3, "right", 110),
        C.Column("星币", 1.3, "right", 110),
    ]
    rows: list[list[tuple]] = []
    for item in trader.manifest:
        rows.append(
            [
                (_item_name(item.item), palette.blue),
                (
                    str(item.prime_price or 0),
                    palette.icon_ducats,
                    icon_char("ducats"),
                    palette.icon_ducats,
                ),
                (
                    _credits_text(item.regular_price or 0),
                    palette.icon_credits,
                    icon_char("credits"),
                    palette.icon_credits,
                ),
            ]
        )
    chips = [("位置", location), ("剩余", time_left)]
    if not rows:
        rows = [[("暂无商品", palette.text_muted), ("—", palette.text_dim), ("—", palette.text_dim)]]
    else:
        rows = _fit_rows(rows, columns, chips, "件")
    size = measure_card_size(
        CardSpec(
            title="虚空商人",
            blocks=[
                ChipsBlock(chips),
                TableBlock(columns=columns, rows=rows),
            ],
            standing="md",
        )
    )

    page = C.new_page(theme, size.width, size.height)
    y = C.draw_header(page, "虚空商人")
    y = C.draw_chips(page, chips, y) + SPACE["md"]
    y = C.draw_table(page, columns, rows, y)
    frame.draw_standing_block(page, y, "md")
    frame.draw_footer_block(page)
    return page.cb.to_image()
