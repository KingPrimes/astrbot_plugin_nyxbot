"""仲裁卡片渲染器 — 迁移自 Java DefaultDrawArbitrationImage

布局：
  - 暗色背景 + 双边框 + 看板娘立绘
  - 标题行：节点 / 敌人 / 任务类型
  - 时间行：开始时间 + 剩余时间
  - 价值判断徽章（值得/不值得参与）— 镜像 Java isWorth()
  - 底部署名
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image

from ..wenum.faction import FactionEnum
from .draw_constant import DrawConstant, ThemeColor, hex_to_rgb
from .font_manager import FontManager
from .image_combiner import ImageCombiner
from .standing import draw_standing

if TYPE_CHECKING:
    from ..model.arbitration import Arbitration
    from .card_renderer import CardRenderer

_CANVAS_W = 800
_MARGIN = 40
_ROW_H = 55

_WORTH_COLOR = (39, 174, 96)       # #27ae60 值得
_NOT_WORTH_COLOR = (231, 76, 60)   # #e74c3c 不值得


def render_arbitration_card(renderer: CardRenderer, arbitration: Arbitration) -> Image.Image:
    """绘制仲裁信息卡片 — 镜像 Java drawArbitrationImage()。

    Args:
        renderer: CardRenderer 实例。
        arbitration: Arbitration 模型实例。

    Returns:
        PIL Image 对象。
    """
    if arbitration is None:
        return renderer.create_text_image("仲裁数据为空", 800, 120)

    canvas_h = 500
    content_x = _MARGIN + 10

    title_font = FontManager.get_text_font(28)
    body_font = FontManager.get_text_font(20)
    footer_font = FontManager.get_text_font(18)

    cb = ImageCombiner(_CANVAS_W, canvas_h, ThemeColor.BG_DARK)
    cb.draw_double_border(
        border_padding=12,
        border_color_outer=ThemeColor.TABLE_BORDER,
        border_color_inner=ThemeColor.DIVIDER,
        stroke=2,
    )

    # 标题
    title_y = _MARGIN + 5
    cb.set_color(ThemeColor.ACCENT_BLUE).set_font(title_font)
    cb.add_centered_text("仲裁任务", title_y)
    cb.set_color(ThemeColor.DIVIDER)
    cb.draw_line(_MARGIN, title_y + 30, _CANVAS_W - _MARGIN, title_y + 30, width=1)

    current_y = _MARGIN + 45

    # 节点
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(body_font)
    cb.add_text(f"节点: {arbitration.node or '未知节点'}", content_x, current_y)

    # 敌人 — 使用 FactionEnum 获取显示名称
    current_y += _ROW_H
    faction: FactionEnum = arbitration.faction
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(body_font)
    cb.add_text(f"敌人: {faction.display_name}", content_x, current_y)

    # 派系图标
    if renderer.font_wf_icon and faction is not FactionEnum.FC_NONE:
        cb.set_color(hex_to_rgb(faction.color)).set_font(renderer.font_wf_icon)
        cb.add_text(faction.icon, content_x + 250, current_y)

    # 任务类型
    current_y += _ROW_H
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(body_font)
    cb.add_text(f"任务类型: {arbitration.type or '未知任务'}", content_x, current_y)

    # 开始时间
    current_y += _ROW_H
    cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(body_font)
    cb.add_text(f"开始时间: {arbitration.activation_str}", content_x, current_y)

    # 剩余时间
    current_y += _ROW_H
    cb.set_color(ThemeColor.ACCENT_GOLD).set_font(body_font)
    cb.add_text(f"剩余时间: {arbitration.time_left}", content_x, current_y)

    # 价值判断 — 镜像 Java isWorth()
    current_y += _ROW_H + 5
    worth_text = "值得参与" if arbitration.is_worth else "不值得参与"
    worth_color = _WORTH_COLOR if arbitration.is_worth else _NOT_WORTH_COLOR
    cb.set_color(worth_color).set_font(FontManager.get_text_font(24))
    cb.add_text(worth_text, content_x, current_y)

    # 看板娘
    draw_standing(cb, max_w=240, max_h=360)

    # 底部署名
    cb.set_color(ThemeColor.TEXT_MUTED).set_font(footer_font)
    cb.add_centered_text(DrawConstant.FOOTER_TEXT, canvas_h - 30)

    return cb.to_image()
