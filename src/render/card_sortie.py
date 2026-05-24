"""突击卡片渲染器 — 迁移自 Java DefaultDrawSortiesImage

采用单列列表布局：
  - 居中标题 + 双层装饰边框
  - Boss 名称行
  - 变体列表（斑马纹背景）
  - 每行显示：任务类型（带颜色）、节点、修饰符
  - 看板娘立绘 + 底部署名
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import ImageFont

from .draw_constant import DrawConstant, ThemeColor
from .font_manager import FontManager
from .image_combiner import ImageCombiner
from .standing import draw_standing

if TYPE_CHECKING:
    from PIL import Image

    from ..model.world_state import Sortie, Variant
    from .card_renderer import CardRenderer


# ---------------------------------------------------------------------------
# 布局常量
# ---------------------------------------------------------------------------

_CANVAS_W = 1200
_MARGIN = 40                       # 双层边框外边距
_CONTENT_PAD = 20                  # 边框内缩进
_CONTENT_X = _MARGIN + _CONTENT_PAD  # 内容区起始 X = 60
_CONTENT_W = _CANVAS_W - 2 * _CONTENT_X  # 1080

_ROW_H = 60                        # 变体行高度
_MIN_HEIGHT = 600                  # 最小画布高度

_TITLE_Y = 70
_DIVIDER_Y = 138
_BOSS_Y = 165                      # Boss 名称行 Y（分割线下方）
_VARIANTS_START_Y = 230

# 看板娘尺寸
_STANDING_MAX_W = 310
_STANDING_MAX_H = 420

_FOOTER_OFFSET = 55


# ---------------------------------------------------------------------------
# 主渲染函数
# ---------------------------------------------------------------------------

def render_sortie_card(renderer: CardRenderer, sortie: Sortie) -> Image.Image:
    """绘制突击信息卡片 — 镜像 Java DefaultDrawSortiesImage.drawSortiesImage()。

    Args:
        renderer: CardRenderer 实例。
        sortie: Sortie 模型。

    Returns:
        PIL Image 对象。
    """
    variants = sortie.variants if sortie.variants else []
    variant_count = len(variants)

    # ---- 动态高度计算 ----
    content_h = (_VARIANTS_START_Y
                 + variant_count * _ROW_H
                 + _STANDING_MAX_H
                 + _FOOTER_OFFSET)
    canvas_h = max(content_h, _MIN_HEIGHT)

    # ---- 字体 ----
    title_font = FontManager.get_text_font(48)
    boss_font = FontManager.get_text_font(28)
    row_font = FontManager.get_text_font(26)
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
    cb.add_centered_text("突击任务", _TITLE_Y)

    # ---- 分割线 ----
    cb.set_color(ThemeColor.DIVIDER)
    cb.draw_line(_CONTENT_X, _DIVIDER_Y, _CONTENT_X + _CONTENT_W, _DIVIDER_Y, width=1)

    # ---- Boss 名称 ----
    _draw_boss_line(cb, sortie, boss_font)

    # ---- 变体列表（斑马纹） ----
    current_y = _VARIANTS_START_Y
    for i, variant in enumerate(variants):
        _draw_variant_row(cb, variant, i, current_y, renderer, row_font)
        current_y += _ROW_H

    # ---- 看板娘 ----
    draw_standing(cb, max_w=_STANDING_MAX_W, max_h=_STANDING_MAX_H)

    # ---- 底部署名 ----
    cb.set_color(ThemeColor.TEXT_MUTED).set_font(footer_font)
    cb.add_centered_text(DrawConstant.FOOTER_TEXT, canvas_h - _FOOTER_OFFSET)

    return cb.to_image()


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _draw_boss_line(
    cb: ImageCombiner,
    sortie: Sortie,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """绘制 Boss 名称行。

    镜像 Java: combiner.addText("Boss: " + sorties.getBoss(), ...)
    """
    boss_name = sortie.boss.display_name if sortie.boss else "未知"
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(font)
    cb.add_text(f"Boss: {boss_name}", _CONTENT_X, _BOSS_Y)


def _draw_variant_row(
    cb: ImageCombiner,
    variant: Variant,
    index: int,
    y: int,
    renderer: CardRenderer,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """绘制单个变体行（斑马纹背景）。

    镜像 Java DefaultDrawSortiesImage 中变体行循环：
      - 奇数行（index % 2 == 1）添加斑马纹背景
      - 任务类型（带颜色）、节点、修饰符

    Args:
        cb: ImageCombiner 实例。
        variant: Variant 模型。
        index: 行索引（0-based）。
        y: 行 Y 坐标。
        renderer: CardRenderer 实例。
        font: 文本字体。
    """
    row_w = _CONTENT_W

    # 斑马纹背景（奇数行）
    if index % 2 == 1:
        cb.set_color(ThemeColor.BG_CARD_ALT)
        cb.fill_rect(_CONTENT_X, y, row_w, _ROW_H)

    # 行内上边距微调
    text_y = y + 15

    # 列 1: 任务类型（带颜色）
    mt = variant.mission_type
    mt_display = mt.display_name if mt else "未知任务"
    mt_color = renderer.resolve_mission_type_color(mt) if mt else ThemeColor.TEXT_SECONDARY
    cb.set_color(mt_color).set_font(font)
    cb.add_text(f"任务: {mt_display}", _CONTENT_X + 20, text_y)

    # 列 2: 节点
    node = variant.node or "未知节点"
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(font)
    cb.add_text(f"节点: {node}", _CONTENT_X + 245, text_y)

    # 列 3: 修饰符
    modifier = variant.modifier_type.display_name if variant.modifier_type else "未知"
    cb.set_color(ThemeColor.WARNING).set_font(font)
    cb.add_text(modifier, _CONTENT_X + 600, text_y)
