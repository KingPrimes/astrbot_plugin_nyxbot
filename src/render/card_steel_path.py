"""钢铁之路卡片渲染器 — 迁移自 Java DefaultDrawSteelPathImage

采用简单列表布局：
  - 居中标题 + 双层装饰边框
  - 当前轮换奖励 + 下一个奖励 + 剩余时间
  - 看板娘立绘 + 底部署名
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .draw_constant import DrawConstant, ThemeColor
from .font_manager import FontManager
from .image_combiner import ImageCombiner
from .standing import draw_standing

if TYPE_CHECKING:
    from PIL import Image

    from ..model.world_state import SteelPathOffering
    from .card_renderer import CardRenderer


# ---------------------------------------------------------------------------
# 布局常量
# ---------------------------------------------------------------------------

_CANVAS_W = 1200
_MARGIN = 40
_CONTENT_PAD = 20
_CONTENT_X = _MARGIN + _CONTENT_PAD
_CONTENT_W = _CANVAS_W - 2 * _CONTENT_X

_ROW_H = 55
_MIN_HEIGHT = 400

_TITLE_Y = 70
_DIVIDER_Y = 138
_CONTENT_START_Y = 180
_FOOTER_OFFSET = 55

_STANDING_MAX_W = 260
_STANDING_MAX_H = 390


# ---------------------------------------------------------------------------
# 主渲染函数
# ---------------------------------------------------------------------------

def render_steel_path_card(
    renderer: CardRenderer,
    steel_path: SteelPathOffering,
) -> Image.Image:
    """绘制钢铁之路信息卡片 — 镜像 Java DefaultDrawSteelPathImage.drawSteelPathImage()。

    Args:
        renderer: CardRenderer 实例。
        steel_path: SteelPathOffering 模型。

    Returns:
        PIL Image 对象。
    """
    # ---- 计算行数（当前奖励 + 下一个奖励 + 剩余时间） ----
    row_count = 0
    if steel_path.current_reward:
        row_count += 1
    if steel_path.next_reward:
        row_count += 1
    row_count += 1  # 剩余时间始终显示

    # ---- 动态高度 ----
    content_h = _CONTENT_START_Y + row_count * _ROW_H + _STANDING_MAX_H + _FOOTER_OFFSET
    canvas_h = max(content_h, _MIN_HEIGHT)

    # ---- 字体 ----
    title_font = FontManager.get_text_font(48)
    body_font = FontManager.get_text_font(28)
    footer_font = FontManager.get_text_font(20)

    # ---- 画布 ----
    cb = ImageCombiner(_CANVAS_W, canvas_h, ThemeColor.BG_DARK)

    # ---- 双层边框 ----
    cb.draw_double_border(
        border_padding=16,
        border_color_outer=ThemeColor.TABLE_BORDER,
        border_color_inner=ThemeColor.DIVIDER,
        stroke=3,
    )

    # ---- 标题 ----
    cb.set_color(ThemeColor.ACCENT_BLUE).set_font(title_font)
    cb.add_centered_text("钢铁奖励", _TITLE_Y)

    # ---- 分割线 ----
    cb.set_color(ThemeColor.DIVIDER)
    cb.draw_line(_CONTENT_X, _DIVIDER_Y, _CONTENT_X + _CONTENT_W, _DIVIDER_Y, width=1)

    # ---- 数据行 ----
    current_y = _CONTENT_START_Y

    # 当前奖励
    if steel_path.current_reward:
        cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(body_font)
        cb.add_text(f"当前奖励: {steel_path.current_reward.name}", _CONTENT_X, current_y + 10)
        current_y += _ROW_H

    # 下一个奖励
    if steel_path.next_reward:
        cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(body_font)
        cb.add_text(f"下一个奖励: {steel_path.next_reward.name}", _CONTENT_X, current_y + 10)
        current_y += _ROW_H

    # 剩余时间
    remaining = steel_path.remaining or "未知"
    cb.set_color(ThemeColor.WARNING).set_font(body_font)
    cb.add_text(f"剩余时间: {remaining}", _CONTENT_X, current_y + 10)

    # ---- 看板娘 ----
    draw_standing(cb, max_w=_STANDING_MAX_W, max_h=_STANDING_MAX_H)

    # ---- 底部署名 ----
    cb.set_color(ThemeColor.TEXT_MUTED).set_font(footer_font)
    cb.add_centered_text(DrawConstant.FOOTER_TEXT, canvas_h - _FOOTER_OFFSET)

    return cb.to_image()
