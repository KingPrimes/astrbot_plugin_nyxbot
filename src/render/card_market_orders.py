"""Market 订单卡片渲染器

两张卡，都是「页头 + 信息条 + 表格 + 提示 + 看板娘 + 署名」的同一套骨架：

* ``render_market_orders_card``：某个物品的在售/求购订单（6 列）；
* ``render_market_orders_possible_items_card``：模糊匹配失败时的候选物品清单（2 列）。

表格用统一的 ``components.draw_table``（斑马纹 + 主题色），
杜卡币 / 交易税带货币图标，卖家状态按在线状态着色，序号给 ``/w <序号>`` 用。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..wenum.icon import IconEnum
from . import card_frame as frame
from . import components as C
from .card_size import CardSpec, ChipsBlock, TableBlock, TextBlock, measure_card_size
from .design import FONT, SPACE, semantic_color
from .theme import current_theme

if TYPE_CHECKING:
    from PIL import Image

    from ..model.market.market_orders import Orders
    from .card_renderer import CardRenderer

#: 订单表列定义。
_ORDER_COLUMNS: tuple[C.Column, ...] = (
    C.Column("#", 0.0, "left", 50),
    C.Column("价格", 0.9, "right", 90),
    C.Column("数量", 0.7, "right", 70),
    C.Column("等级", 0.7, "right", 70),
    C.Column("卖家", 2.4, "left", 200),
    C.Column("状态", 1.0, "left", 90),
)

#: 候选物品清单列定义。
_ITEM_COLUMNS: tuple[C.Column, ...] = (
    C.Column("序号", 0.0, "left", 60),
    C.Column("物品名称", 3.0, "left", 280),
)

#: 平台 → 语义色（会按主题校正）。
_PLATFORM_COLORS: dict[str, str] = {
    "pc": "#4585E9",
    "ps4": "#3498DB",
    "xbox": "#2ECC71",
    "switch": "#E67E22",
    "mobile": "#9B59B6",
}

_WHISPER_HINT = "回复 /w 序号 获取对应卖家的私聊语句（2 分钟内有效）"


def _platform_color(form: str, theme):
    """平台 → 主题适配色。"""
    return semantic_color(
        _PLATFORM_COLORS.get((form or "pc").lower(), "#4585E9"), theme, theme.palette.text_muted
    )


def _order_rows(orders: Orders, palette) -> list[list[tuple]]:
    """订单列表 → 表格行。"""
    req_mastery = orders.req_mastery_rank or 0
    rows: list[list[tuple]] = []

    for index, order in enumerate(orders.orders, 1):
        rank = order.rank
        rank_color = palette.text
        if rank is not None and req_mastery > 0:
            ratio = min(rank / req_mastery, 1.0)
            if ratio >= 0.9:
                rank_color = palette.green
            elif ratio >= 0.5:
                rank_color = palette.blue

        user = order.user
        seller = (user.ingame_name if user and user.ingame_name else "未知卖家")
        status = (user.status if user and user.status else "")

        rows.append(
            [
                (str(index), palette.text_muted),
                (str(order.platinum) if order.platinum is not None else "-", palette.gold),
                (str(order.quantity) if order.quantity is not None else "-", palette.text),
                (str(rank) if rank is not None else "-", rank_color),
                (seller, palette.text),
                (_status_label(status), C.status_color(status, palette)),
            ]
        )
    return rows


def _status_label(status: str) -> str:
    """在线状态 → 中文文案。"""
    return {
        "online": "在线",
        "ingame": "游戏中",
        "offline": "离线",
        "invisible": "隐身",
    }.get((status or "").lower(), status or "未知")


def _info_chips(orders: Orders, theme) -> list[tuple]:
    """信息条：平台 / 买卖 / 段位 / 入库 / 杜卡币 / 交易税。"""
    palette = theme.palette
    chips: list[tuple] = [
        ("平台", (orders.form or "pc").upper()),
        ("类型", "买家" if orders.is_by else "卖家"),
    ]
    if orders.req_mastery_rank:
        chips.append(("段位", f"MR {orders.req_mastery_rank}"))
    if orders.vaulted:
        chips.append(("状态", "已入库"))

    chips.append(("杜卡币", str(orders.ducats), IconEnum.DUCATS.icon, palette.icon_ducats))
    chips.append(
        ("交易税", f"{orders.trading_tax:,}", IconEnum.CREDITS.icon, palette.icon_credits)
    )
    return chips


def render_market_orders_card(
    renderer: CardRenderer,
    orders: Orders,
) -> Image.Image:
    """绘制 Market 订单卡片。

    Args:
        renderer: CardRenderer 实例（空数据时用它出提示图）。
        orders: Orders 模型。

    Returns:
        PIL Image 对象。
    """
    if not orders.orders:
        return renderer.create_text_image(f"没有找到 {orders.name} 的订单数据", 800, 120)

    theme = current_theme()
    chips = _info_chips(orders, theme)
    rows = _order_rows(orders, theme.palette)
    subtitle = f"共 {len(rows)} 条订单"

    size = measure_card_size(
        CardSpec(
            title=orders.name,
            subtitle=subtitle,
            blocks=[
                ChipsBlock(chips),
                TableBlock(columns=_ORDER_COLUMNS, rows=rows, gap=SPACE["lg"]),
                TextBlock(lines=[_WHISPER_HINT], size="base"),
            ],
            standing="md",
        )
    )

    page = C.new_page(theme, size.width, size.height)
    y = C.draw_header(page, orders.name, subtitle)
    y = C.draw_chips(page, chips, y) + SPACE["md"]
    table_bottom = C.draw_table(page, _ORDER_COLUMNS, rows, y)

    hint_top = table_bottom + SPACE["lg"]
    C.draw_hint(page, _WHISPER_HINT, hint_top)
    frame.draw_standing_block(page, hint_top + FONT["base"] + SPACE["xs"], "md")
    frame.draw_footer_block(page)
    return page.cb.to_image()


def render_market_orders_possible_items_card(
    renderer: CardRenderer,
    possible_items: list[str],
    hint: str = "",
) -> Image.Image:
    """绘制「可能要查询的物品」候选清单卡片。

    Args:
        renderer: CardRenderer 实例（空数据时用它出提示图）。
        possible_items: 物品名称列表（最多 15 条）。
        hint: 副标题，通常写「回复 /WM 1~8 查询（60 秒内有效）」；
            为空时退化为「请用更完整的名称重试」。

    Returns:
        PIL Image 对象。
    """
    if not possible_items:
        return renderer.create_text_image("没有找到匹配的物品", 800, 120)

    theme = current_theme()
    palette = theme.palette
    items = possible_items[:15]
    rows: list[list[tuple]] = [
        [(str(index), palette.gold), (item, palette.text)]
        for index, item in enumerate(items, 1)
    ]

    size = measure_card_size(
        CardSpec(
            title="未精确匹配，以下是可能的物品",
            subtitle=hint or "请用更完整的名称重试",
            blocks=[TableBlock(columns=_ITEM_COLUMNS, rows=rows)],
            standing="md",
            header_gap=SPACE["md"],
        )
    )

    page = C.new_page(theme, size.width, size.height)
    y = C.draw_header(page, "未精确匹配，以下是可能的物品", hint or "请用更完整的名称重试")
    C.draw_table(page, _ITEM_COLUMNS, rows, y + SPACE["md"])

    frame.draw_standing_block(page, y + SPACE["md"] + C.table_height(len(rows)), "md")
    frame.draw_footer_block(page)
    return page.cb.to_image()
