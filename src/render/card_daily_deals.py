"""每日特惠卡片渲染器

对应 Java DefaultDrawDailyDealsImage.java。
固定 1000x600 画布，包含双层边框、看板娘立绘、底部署名。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .draw_constant import DrawConstant, ThemeColor
from .font_manager import FontManager
from .image_combiner import ImageCombiner
from .standing import draw_standing

if TYPE_CHECKING:
    from PIL import Image

    from ..model.world_state import DailyDeals
    from .card_renderer import CardRenderer

# 画布尺寸 — 对应 Java DAILY_DEALS_IMAGE_WIDTH/HEIGHT
_CANVAS_W = 1000
_CANVAS_H = 600

_ORIGINAL_PRICE_COLOR = (0xFF, 0x6B, 0x6B)
_SALE_PRICE_COLOR = (0x4C, 0xAF, 0x50)
_DISCOUNT_COLOR = (0xFF, 0x6B, 0x6B)
_REMAINING_COLOR = (0x4C, 0xAF, 0x50)

# Java 暗色背景 — PAGE_BACKGROUND_COLOR
_PAGE_BG = ThemeColor.BG_DARK


def render_daily_deals_card(
    renderer: CardRenderer,
    deals: list[DailyDeals],
) -> Image.Image:
    """绘制每日特惠卡片 — 对应 Java drawDailyDealsImage()。

    Args:
        renderer: CardRenderer 实例。
        deals: DailyDeals 模型列表（仅渲染第一个）。
    """
    if not deals:
        return renderer.create_text_image("当前没有每日特惠数据")

    d = deals[0]

    # 使用更大的字体，适配 1000x600 画布
    title_font = FontManager.get_text_font(56)
    body_font = FontManager.get_text_font(30)
    FontManager.get_text_font(20)

    cb = ImageCombiner(_CANVAS_W, _CANVAS_H, _PAGE_BG)

    # 双层边框 — 对应 Java drawTooRoundRect()
    cb.draw_double_border()

    # 看板娘 — 对应 Java drawStandingDrawing()
    draw_standing(cb)

    # 标题 — 对应 Java addCenteredText("每日特惠", 80)
    cb.set_color(ThemeColor.ACCENT_BLUE).set_font(title_font)
    cb.add_centered_text("每日特惠", 70)

    label_x = DrawConstant.IMAGE_MARGIN  # 40
    value_x = 300
    row_h = 70
    start_y = 160

    # ── 物品名称 ──
    item_name = d.item or "未知物品"
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(body_font)
    cb.add_text("物品名称:", label_x, start_y)
    cb.add_text(item_name, value_x, start_y)

    start_y += row_h

    # ── 原价/现价（原价红色 + 删除线） ──
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(body_font)
    cb.add_text("原价/现价:", label_x, start_y)

    original = d.original_price or 0
    sale = d.sale_price or 0
    original_str = str(original)

    cb.set_color(_ORIGINAL_PRICE_COLOR)
    cb.add_text(original_str, value_x, start_y)
    price_w = cb.get_string_width(original_str)
    # 删除线 — 偏移量适配 30px 字体
    cb.draw_line(value_x, start_y + 22, value_x + price_w, start_y + 22, width=2)

    cb.set_color(ThemeColor.TEXT_PRIMARY)
    cb.add_text(" / ", value_x + price_w, start_y)

    cb.set_color(_SALE_PRICE_COLOR)
    cb.add_text(str(sale), value_x + price_w + 40, start_y)

    start_y += row_h

    # ── 折扣比 ──
    discount = d.discount or 0
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(body_font)
    cb.add_text("折扣比:", label_x, start_y)
    cb.set_color(_DISCOUNT_COLOR)
    cb.add_text(f"{discount:.0f}%", value_x, start_y)

    start_y += row_h

    # ── 总/余 ──
    total = d.total or 0
    sold = d.sold or 0
    remaining = total - sold
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(body_font)
    cb.add_text("总/余:", label_x, start_y)
    cb.add_text(str(total), value_x, start_y)
    total_w = cb.get_string_width(str(total))
    cb.add_text(" / ", value_x + total_w, start_y)
    cb.set_color(_REMAINING_COLOR)
    cb.add_text(str(remaining), value_x + total_w + 40, start_y)

    start_y += row_h

    # ── 剩余时间 ──
    time_left = d.time_left or "未知"
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(body_font)
    cb.add_text("剩余时间:", label_x, start_y)
    cb.set_color(ThemeColor.ACCENT)
    cb.add_text(time_left, value_x, start_y)

    # 底部署名 — 对应 Java addFooter(combiner, height - IMAGE_FOOTER_HEIGHT)
    cb.draw_card_footer(_CANVAS_H)

    return cb.to_image()
