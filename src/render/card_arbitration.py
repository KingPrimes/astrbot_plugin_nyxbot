"""仲裁卡片渲染器 — 对齐 Go draw_arbitration.go

两条渲染入口，共用同一块「两列三行」面板：

* ``render_arbitration_card``      单条：页头 + 面板 + 看板娘 + 署名
* ``render_arbitration_list_card`` 前瞻：页头 + 2 列卡片网格 + 看板娘 + 署名

面板字段：节点 / 敌人（带派系图标）、任务类型 / 开始、剩余 / 评级。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from . import card_frame as frame
from . import components as C
from .card_size import CardSpec, CustomBlock, measure_card_size
from .design import FONT, SPACE, adapt_color, font
from .theme import current_theme

if TYPE_CHECKING:
    from PIL import Image

    from ..model.arbitration import ArbitrationView
    from .card_renderer import CardRenderer

#: 评级颜色 — 对齐 Go tierSColor..tierFColor
_TIER_COLORS: dict[str, str] = {
    "S": "#FFC107",
    "A": "#E040FB",
    "B": "#42A5F5",
    "C": "#66BB6A",
    "D": "#9E9E9E",
    "F": "#757575",
}


def _tier_label(tier: str) -> str:
    normalized = (tier or "").strip().upper()
    return normalized if normalized in _TIER_COLORS else "F"


def _faction_label(faction) -> str:
    from ..wenum.faction import FactionEnum

    if faction is FactionEnum.FC_NONE:
        return "未知"
    return faction.display_name or "未知"


def _row_height(compact: bool) -> int:
    """一行 = 值的一行 + 行间呼吸（标签与值同行）。"""
    return (FONT["sm"] if compact else FONT["md"]) + SPACE["md"]


def _panel_height(compact: bool) -> int:
    return SPACE["lg"] * 2 + _row_height(compact) * 3


def _draw_panel(
    page,
    view: ArbitrationView,
    x: int,
    y: int,
    width: int,
    compact: bool = False,
) -> int:
    """画一块仲裁面板（左/右两列，每列 3 行「标签 + 值」），返回底部 y。"""
    from ..wenum.faction import FactionEnum

    theme = page.theme
    palette = page.palette
    cb = page.cb
    height = _panel_height(compact)
    C.draw_grid_card(page, x, y, width, height)

    value_size = FONT["sm"] if compact else FONT["md"]
    value_font = font("sm") if compact else font("md")
    label_font = font("xs") if compact else font("sm")
    row_h = _row_height(compact)
    pad = SPACE["lg"]

    inner_w = width - pad * 2
    col_gap = SPACE["xl"]
    left_x = x + pad
    right_x = x + pad + (inner_w - col_gap) // 2 + col_gap
    top = y + pad

    # 同一块面板内标签列对齐
    labels = ("节点", "任务类型", "剩余", "敌人", "开始", "评级")
    label_w = max(C.measure(label, label_font) for label in labels)
    # 单列可用宽度：卡片内容宽的一半，减去标签与图标；值超宽必须截断，
    # 否则会像旧版一样顶出卡片（列表卡尤其明显）。
    column_w = (inner_w - col_gap) // 2
    value_max = column_w - label_w - SPACE["md"]

    def field(
        cx: int,
        cy: int,
        label: str,
        value: str,
        color=None,
        icon: str | None = None,
    ) -> None:
        cb.set_color(palette.text_dim).set_font(label_font)
        cb.add_text(label, cx, cy + (value_size - label_font.size) // 2 + 2)

        value_x = cx + label_w + SPACE["md"]
        available = value_max
        if icon:
            tint = color or palette.text
            cb.set_color(tint).set_font(C.icon_font(value_size))
            cb.add_text(icon, value_x, cy)
            icon_w = value_size + SPACE["xs"]
            value_x += icon_w
            available -= icon_w

        cb.set_color(color or palette.text).set_font(value_font)
        cb.add_text(C.fit_text(value, max(20, available), value_font), value_x, cy)

    fraction = view.faction
    faction_color = (
        adapt_color(fraction.color, theme)
        if fraction is not FactionEnum.FC_NONE
        else palette.text_muted
    )

    # 左列：节点 / 任务类型 / 剩余
    field(left_x, top, "节点", view.node or "未知节点")
    field(left_x, top + row_h, "任务类型", view.mission_name or "未知")
    field(left_x, top + row_h * 2, "剩余", view.time_left, palette.gold)

    # 右列：敌人（派系图标）/ 开始 / 评级
    faction_icon = fraction.icon if fraction is not FactionEnum.FC_NONE else None
    field(right_x, top, "敌人", _faction_label(fraction), faction_color, faction_icon)
    # 紧凑卡空间有限，开始时间省掉年份与秒
    activation = (
        view.activation.strftime("%m-%d %H:%M") if compact else view.activation_str
    )
    field(right_x, top + row_h, "开始", activation, palette.text_muted)
    field(
        right_x,
        top + row_h * 2,
        "评级",
        _tier_label(view.tier),
        adapt_color(_TIER_COLORS[_tier_label(view.tier)], theme),
    )
    return y + height


def render_arbitration_card(
    renderer: CardRenderer,
    arbitration: ArbitrationView,
) -> Image.Image:
    """绘制单条仲裁卡片 — 对齐 Go DrawArbitration。"""
    if arbitration is None:
        return renderer.create_text_image("仲裁数据为空", 800, 120)

    theme = current_theme()
    panel_h = _panel_height(compact=False)
    size = measure_card_size(
        CardSpec(
            title="仲裁任务",
            blocks=[CustomBlock(width=760, height=panel_h)],
            standing="md",
            header_gap=SPACE["md"],
        )
    )

    page = C.new_page(theme, size.width, size.height)
    y = C.draw_header(page, "仲裁任务")
    y = _draw_panel(page, arbitration, page.content_x, y + SPACE["md"], page.content_w)
    frame.draw_standing_block(page, y, "md")
    frame.draw_footer_block(page)
    return page.cb.to_image()


def render_arbitration_list_card(
    renderer: CardRenderer,
    arbitrations: list[ArbitrationView],
) -> Image.Image:
    """绘制仲裁前瞻列表 — 对齐 Go DrawArbitrations。"""
    if not arbitrations:
        return renderer.create_text_image("暂无可参与的仲裁数据", 800, 120)

    theme = current_theme()
    cards = arbitrations[:10]
    columns = 2
    gap = SPACE["lg"]

    # 两张并排卡，每张要容得下「标签 + 时间」两列，720 宽会挤爆
    panel_h = _panel_height(compact=True)
    rows = (len(cards) + columns - 1) // columns
    grid_h = rows * panel_h + max(0, rows - 1) * gap

    # 第一遍：拿到画布宽度才能算卡片宽与看板娘空位
    provisional = measure_card_size(
        CardSpec(
            title="有价值的仲裁任务",
            blocks=[CustomBlock(width=1120, height=grid_h)],
            standing=None,
        )
    )
    content_w = provisional.content_width
    card_w = (content_w - gap) // columns

    # 奇数张时最后一格空着 → 看板娘填进去；偶数张才走流式块
    slot_index = len(cards)
    cell_standing = (
        frame.standing_cell_size(card_w, panel_h * 2)
        if slot_index < rows * columns
        else (0, 0)
    )
    extra_h = (
        max(0, cell_standing[1] - panel_h) + SPACE["md"]
        if cell_standing[1]
        else frame.standing_block_height("md", content_w)
    )

    # 第二遍：把空位里立绘溢出的高度补进画布
    size = measure_card_size(
        CardSpec(
            title="有价值的仲裁任务",
            blocks=[CustomBlock(width=1120, height=grid_h + extra_h)],
            standing=None,
        )
    )

    page = C.new_page(theme, size.width, size.height)
    y = C.draw_header(page, "有价值的仲裁任务")

    for index, view in enumerate(cards):
        row, column = divmod(index, columns)
        x = page.content_x + column * (card_w + gap)
        top = y + row * (panel_h + gap)
        _draw_panel(page, view, x, top, card_w, compact=True)

    if cell_standing[1]:
        slot_row, slot_col = divmod(slot_index, columns)
        frame.draw_standing_in_cell(
            page,
            page.content_x + slot_col * (card_w + gap),
            y + slot_row * (panel_h + gap),
            card_w,
            panel_h * 2,
        )
    else:
        frame.draw_standing_block(page, y + grid_h, "md")

    frame.draw_footer_block(page)
    return page.cb.to_image()
