"""Market 订单卡片渲染器

布局：
  - 1000px 宽，独立画布大小
  - 双层装饰边框 + 居中标题 + 信息栏 + 数据表格
  - 右下角看板娘立绘 + 底部署名
  - 杜卡币、交易税数值后方带有对应图标
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image, ImageFont

from ..wenum.icon import IconEnum
from .draw_constant import LayoutConstants, ThemeColor
from .font_manager import FontManager
from .image_combiner import ImageCombiner
from .standing import draw_standing

if TYPE_CHECKING:
    from ..model.market.market_orders import Orders, OrderWithUser
    from .card_renderer import CardRenderer

# ---------------------------------------------------------------------------
# 布局常量
# ---------------------------------------------------------------------------

_CANVAS_W = 1000
_CONTENT_X, _CONTENT_W = LayoutConstants.get_content_bounds(_CANVAS_W)

_ROW_H = 52
_TABLE_HEADER_H = 46

_TITLE_Y = 70
_DIVIDER_Y = 135
_INFO_BAR_Y = 155
_INFO_ROW2_Y = 208
_TABLE_START_Y = 262

_FOOTER_OFFSET = 55

_STANDING_MAX_W = 310
_STANDING_MAX_H = 420

_MIN_HEIGHT = 700

# 表格列宽（总和 = 880 = _CONTENT_W）
_COL_INDEX_W = 60
_COL_PRICE_W = 130
_COL_QUANTITY_W = 120
_COL_RANK_W = 130
_COL_SELLER_W = 260
_COL_STATUS_W = 180

# 列起始 X 坐标（相对于 _CONTENT_X）
_COL_INDEX_X = _CONTENT_X
_COL_PRICE_X = _CONTENT_X + _COL_INDEX_W
_COL_QUANTITY_X = _COL_PRICE_X + _COL_PRICE_W
_COL_RANK_X = _COL_QUANTITY_X + _COL_QUANTITY_W
_COL_SELLER_X = _COL_RANK_X + _COL_RANK_W
_COL_STATUS_X = _COL_SELLER_X + _COL_SELLER_W

_WHISPER_HINT = "回复 /w 序号 获取对应卖家的私聊语句（2 分钟内有效）"
"""卡片底部提示。"""

# 颜色常量
_TABLE_HEADER_BG = (41, 128, 185)           # #2980B9

_PLATFORM_COLORS: dict[str, tuple[int, int, int]] = {
    "pc": (69, 133, 233),
    "ps4": (52, 152, 219),
    "xbox": (46, 204, 113),
    "switch": (230, 126, 34),
    "mobile": (155, 89, 182),
}

# 信息栏元素间距
_INFO_GAP = 16


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _get_platform_color(platform: str) -> tuple[int, int, int]:
    """获取平台对应的主题色。"""
    return _PLATFORM_COLORS.get(platform.lower(), ThemeColor.ACCENT_BLUE)


def _draw_info_bar(
    cb: ImageCombiner,
    orders: Orders,
    info_label_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    info_value_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    icon_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """绘制信息栏。

    单行布局：左侧平台+买卖切换，右侧杜卡币+交易税。
    纯文本无 pill 背景，仅通过颜色区分各元素状态。

    性能优化：所有宽度测量集中在 Phase 1，Phase 2 纯绘制，
    减少 font 切换和 textbbox 调用次数。
    """
    y1 = _INFO_BAR_Y
    right_edge = _CONTENT_X + _CONTENT_W

    # ---- Phase 1: 批量测量所有文本宽度 ----
    tax_text = f"{orders.trading_tax:,}"
    ducats_text = str(orders.ducats)
    plat_text = orders.form.upper() if orders.form else "PC"

    cb.set_font(info_value_font)
    tax_val_w = cb.get_string_width(tax_text)
    duc_val_w = cb.get_string_width(ducats_text)
    plat_w = cb.get_string_width(plat_text)
    buyer_w = cb.get_string_width("买家")

    cb.set_font(icon_font)
    credits_icon_w = cb.get_string_width(IconEnum.CREDITS.icon)
    ducats_icon_w = cb.get_string_width(IconEnum.DUCATS.icon)

    cb.set_font(info_label_font)
    tax_label_w = cb.get_string_width("交易税:")
    duc_label_w = cb.get_string_width("杜卡币:")
    buyer_slash_w = cb.get_string_width("买家 / ")
    mr_label_w = cb.get_string_width("段位:")

    # 计算右侧组位置
    tax_group_w = tax_label_w + 4 + tax_val_w + 4 + credits_icon_w
    duc_group_w = duc_label_w + 4 + duc_val_w + 4 + ducats_icon_w
    right_group_w = duc_group_w + _INFO_GAP + tax_group_w
    right_start_x = right_edge - right_group_w

    # ---- Phase 2: 绘制 ----

    # 右侧：杜卡币组
    cursor = right_start_x
    cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(info_label_font)
    cb.add_text("杜卡币:", cursor, y1 + 10)
    cursor += duc_label_w + 4

    cb.set_color(ThemeColor.ACCENT_GOLD).set_font(info_value_font)
    cb.add_text(ducats_text, cursor, y1 + 8)
    cursor += duc_val_w + 4

    cb.set_color(ThemeColor.ACCENT_GOLD).set_font(icon_font)
    cb.add_text(IconEnum.DUCATS.icon, cursor, y1 + 8)

    # 右侧：交易税组
    cursor = right_start_x + duc_group_w + _INFO_GAP
    cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(info_label_font)
    cb.add_text("交易税:", cursor, y1 + 10)
    cursor += tax_label_w + 4

    cb.set_color(ThemeColor.ACCENT_BLUE).set_font(info_value_font)
    cb.add_text(tax_text, cursor, y1 + 8)
    cursor += tax_val_w + 4

    cb.set_color(ThemeColor.ACCENT_BLUE).set_font(icon_font)
    cb.add_text(IconEnum.CREDITS.icon, cursor, y1 + 8)

    # 左侧：平台
    cursor = _CONTENT_X
    plat_color = _get_platform_color(orders.form or "pc")
    cb.set_color(plat_color).set_font(info_value_font)
    cb.add_text(plat_text, cursor, y1 + 8)
    cursor += plat_w + _INFO_GAP

    # 左侧：买卖切换
    if orders.is_by:
        cb.set_color(ThemeColor.SUCCESS).set_font(info_value_font)
        cb.add_text("买家", cursor, y1 + 8)
        cursor += buyer_w
        cb.set_color(ThemeColor.TEXT_MUTED).set_font(info_label_font)
        cb.add_text(" / 卖家", cursor, y1 + 10)
    else:
        cb.set_color(ThemeColor.TEXT_MUTED).set_font(info_label_font)
        cb.add_text("买家 / ", cursor, y1 + 10)
        cursor += buyer_slash_w
        cb.set_color(ThemeColor.SUCCESS).set_font(info_value_font)
        cb.add_text("卖家", cursor, y1 + 8)

    # 第二行：段位 + 已入库
    if (orders.req_mastery_rank and orders.req_mastery_rank > 0) or orders.vaulted:
        y2 = _INFO_ROW2_Y
        cursor = _CONTENT_X

        if orders.req_mastery_rank and orders.req_mastery_rank > 0:
            cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(info_label_font)
            cb.add_text("段位:", cursor, y2 + 10)
            cursor += mr_label_w + 4

            mr_color = ThemeColor.WARNING if orders.req_mastery_rank >= 12 else ThemeColor.ACCENT_GOLD
            cb.set_color(mr_color).set_font(info_value_font)
            mr_text = f"MR {orders.req_mastery_rank}"
            cb.add_text(mr_text, cursor, y2 + 8)
            cursor += cb.get_string_width(mr_text) + _INFO_GAP

        if orders.vaulted:
            cb.set_color(ThemeColor.DANGER).set_font(info_value_font)
            cb.add_text("已入库", cursor, y2 + 8)


def _draw_table_header(
    cb: ImageCombiner,
    header_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """绘制表格表头行。"""
    cb.set_color(_TABLE_HEADER_BG)
    cb.fill_rect(_CONTENT_X, _TABLE_START_Y, _CONTENT_W, _TABLE_HEADER_H)

    headers = [
        ("#", _COL_INDEX_X),
        ("价格", _COL_PRICE_X),
        ("数量", _COL_QUANTITY_X),
        ("等级", _COL_RANK_X),
        ("卖家", _COL_SELLER_X),
        ("状态", _COL_STATUS_X),
    ]
    cb.set_color((255, 255, 255)).set_font(header_font)
    text_y = _TABLE_START_Y + _TABLE_HEADER_H // 2 - 4
    for text, x in headers:
        cb.add_text(text, x + 14, text_y)


def _draw_order_row(
    cb: ImageCombiner,
    order: OrderWithUser,
    row_y: int,
    row_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    row_index: int,
    req_mastery_rank: int,
) -> None:
    """绘制单条订单数据行。"""
    # 斑马条纹
    if row_index % 2 == 1:
        cb.set_color(ThemeColor.BG_CARD_ALT)
        cb.fill_rect(_CONTENT_X, row_y, _CONTENT_W, _ROW_H)

    text_y = row_y + _ROW_H // 2 - 4

    platinum = str(order.platinum) if order.platinum is not None else "-"
    quantity = str(order.quantity) if order.quantity is not None else "-"
    rank = str(order.rank) if order.rank is not None else "-"
    seller = "未知"
    status = "未知"
    if order.user is not None:
        seller = order.user.ingame_name or "未知"
        status = order.user.status or "未知"

    # 序号（配合 /w <序号> 取私聊语句）
    cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(row_font)
    cb.add_text(str(row_index + 1), _COL_INDEX_X + 14, text_y)

    # 价格（白金）
    cb.set_color(ThemeColor.ACCENT_GOLD).set_font(row_font)
    cb.add_text(platinum, _COL_PRICE_X + 14, text_y)

    # 数量
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(row_font)
    cb.add_text(quantity, _COL_QUANTITY_X + 14, text_y)

    # 等级
    rank_color = ThemeColor.TEXT_PRIMARY
    if order.rank is not None and req_mastery_rank and req_mastery_rank > 0:
        ratio = min(order.rank / req_mastery_rank, 1.0)
        if ratio >= 0.9:
            rank_color = ThemeColor.SUCCESS
        elif ratio >= 0.5:
            rank_color = ThemeColor.ACCENT_BLUE
    cb.set_color(rank_color).set_font(row_font)
    cb.add_text(rank, _COL_RANK_X + 14, text_y)

    # 卖家
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(row_font)
    cb.add_text(seller, _COL_SELLER_X + 14, text_y)

    # 状态（带颜色）
    cb.set_color(ThemeColor.get_status_color(status)).set_font(row_font)
    cb.add_text(status, _COL_STATUS_X + 14, text_y)


# ---------------------------------------------------------------------------
# 主渲染函数
# ---------------------------------------------------------------------------

def render_market_orders_card(
    renderer: CardRenderer,
    orders: Orders,
) -> Image.Image:
    """绘制 Market 订单卡片。

    Args:
        renderer: CardRenderer 实例。
        orders: Orders 模型。

    Returns:
        PIL Image 对象。
    """
    order_list = orders.orders
    if not order_list:
        return renderer.create_text_image(
            f"没有找到 {orders.name} 的订单数据", 800, 120
        )

    # ---- 动态高度 ----
    row_count = len(order_list)
    table_h = _TABLE_HEADER_H + row_count * _ROW_H
    content_bottom = _TABLE_START_Y + table_h + 46
    canvas_h = max(content_bottom + _STANDING_MAX_H + _FOOTER_OFFSET, _MIN_HEIGHT)

    # ---- 字体 ----
    title_font = FontManager.get_text_font(48)
    info_label_font = FontManager.get_text_font(22)
    info_value_font = FontManager.get_text_font(24)
    header_font = FontManager.get_text_font(22)
    row_font = FontManager.get_text_font(20)
    FontManager.get_text_font(20)
    icon_font = FontManager.get_wf_icon_font(24)

    # ---- 画布 + 双层边框 ----
    cb = ImageCombiner(_CANVAS_W, canvas_h, ThemeColor.BG_DARK)
    cb.draw_default_double_border()

    # ---- 标题 ----
    cb.set_color(ThemeColor.ACCENT_BLUE).set_font(title_font)
    cb.add_centered_text(orders.name, _TITLE_Y)

    # ---- 分割线 ----
    cb.draw_content_divider(_DIVIDER_Y, _CONTENT_X, _CONTENT_W)

    # ---- 信息栏 ----
    _draw_info_bar(cb, orders, info_label_font, info_value_font, icon_font)

    # ---- 表格表头 ----
    _draw_table_header(cb, header_font)

    # ---- 数据行 ----
    for i, order in enumerate(order_list):
        row_y = _TABLE_START_Y + _TABLE_HEADER_H + i * _ROW_H
        _draw_order_row(cb, order, row_y, row_font, i, orders.req_mastery_rank or 0)

    # ---- 私聊提示 ----
    cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(header_font)
    cb.add_centered_text(_WHISPER_HINT, _TABLE_START_Y + table_h + 14)

    # ---- 看板娘 ----
    draw_standing(cb, max_w=_STANDING_MAX_W, max_h=_STANDING_MAX_H)

    # ---- 底部署名 ----
    cb.draw_card_footer(canvas_h)

    return cb.to_image()


def render_market_orders_possible_items_card(
    renderer: CardRenderer,
    possible_items: list[str],
    hint: str = "",
) -> Image.Image:
    """绘制"可能要查询的物品列表"卡片。

    Args:
        renderer: CardRenderer 实例。
        possible_items: 物品名称列表。
        hint: 卡片副标题，通常写「回复 /WM 1~8 查询（60 秒内有效）」；
            为空时退化为「未精确匹配，以下是可能的物品」。

    Returns:
        PIL Image 对象。
    """
    if not possible_items:
        return renderer.create_text_image("没有找到匹配的物品", 800, 120)

    possible_items = possible_items[:15]

    # ---- 动态高度 ----
    item_count = len(possible_items)
    list_h = _TABLE_HEADER_H + item_count * _ROW_H
    content_bottom = _DIVIDER_Y + 60 + list_h
    canvas_h = max(content_bottom + _STANDING_MAX_H + _FOOTER_OFFSET, _MIN_HEIGHT)

    # ---- 字体 ----
    title_font = FontManager.get_text_font(36)
    header_font = FontManager.get_text_font(22)
    row_font = FontManager.get_text_font(20)
    FontManager.get_text_font(20)

    # ---- 画布 + 双层边框 ----
    cb = ImageCombiner(_CANVAS_W, canvas_h, ThemeColor.BG_DARK)
    cb.draw_default_double_border()

    # ---- 标题 ----
    cb.set_color(ThemeColor.ACCENT_BLUE).set_font(title_font)
    cb.add_centered_text("未精确匹配，以下是可能的物品", _TITLE_Y)

    # ---- 分割线 ----
    cb.draw_content_divider(_DIVIDER_Y, _CONTENT_X, _CONTENT_W)

    # ---- 子标题：怎么用编号 ----
    cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(header_font)
    cb.add_centered_text(hint or "请用更完整的名称重试", _DIVIDER_Y + 38)

    # ---- 列表表头 ----
    list_start_y = _DIVIDER_Y + 65
    cb.set_color(_TABLE_HEADER_BG)
    cb.fill_rect(_CONTENT_X, list_start_y, _CONTENT_W, _TABLE_HEADER_H)
    cb.set_color((255, 255, 255)).set_font(header_font)
    text_y = list_start_y + _TABLE_HEADER_H // 2 - 4
    cb.add_text("序号", _CONTENT_X + 20, text_y)
    cb.add_text("物品名称", _CONTENT_X + 150, text_y)

    # ---- 列表行 ----
    for idx, item in enumerate(possible_items, 1):
        row_y = list_start_y + _TABLE_HEADER_H + (idx - 1) * _ROW_H
        if idx % 2 == 1:
            cb.set_color(ThemeColor.BG_CARD_ALT)
            cb.fill_rect(_CONTENT_X, row_y, _CONTENT_W, _ROW_H)

        row_text_y = row_y + _ROW_H // 2 - 4

        cb.set_color(ThemeColor.ACCENT_GOLD).set_font(row_font)
        cb.add_text(str(idx), _CONTENT_X + 20, row_text_y)

        cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(row_font)
        cb.add_text(item, _CONTENT_X + 150, row_text_y)

    # ---- 看板娘 ----
    draw_standing(cb, max_w=_STANDING_MAX_W, max_h=_STANDING_MAX_H)

    # ---- 底部署名 ----
    cb.draw_card_footer(canvas_h)

    return cb.to_image()
