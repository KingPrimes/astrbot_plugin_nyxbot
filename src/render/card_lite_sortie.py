"""执刑官猎杀卡片渲染器 — 迁移自 Java DefaultDrawLiteSortieImage

采用单列列表布局：
  - 居中标题 + 双层装饰边框
  - Boss 名称 + 结束时间
  - 任务列表（带颜色的任务类型 + 节点名）
  - 看板娘立绘 + 底部署名
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from PIL import ImageFont

from .draw_constant import LayoutConstants, ThemeColor
from .font_manager import FontManager
from .image_combiner import ImageCombiner
from .standing import draw_standing

if TYPE_CHECKING:
    from PIL import Image

    from ..model.world_state import LiteSortie, Mission
    from .card_renderer import CardRenderer


# ---------------------------------------------------------------------------
# 布局常量
# ---------------------------------------------------------------------------

_CANVAS_W = 900
_CONTENT_X, _CONTENT_W = LayoutConstants.get_content_bounds(_CANVAS_W)

_ROW_H = 50
_MIN_HEIGHT = 600

_TITLE_Y = 70
_DIVIDER_Y = 138
_INFO_START_Y = 160
_MISSIONS_START_Y = 260
_FOOTER_OFFSET = 55

_STANDING_MAX_W = 240
_STANDING_MAX_H = 360


# ---------------------------------------------------------------------------
# 主渲染函数
# ---------------------------------------------------------------------------

def render_lite_sortie_card(
    renderer: CardRenderer,
    lite_sortie: LiteSortie,
) -> Image.Image:
    """绘制执刑官猎杀信息卡片 — 镜像 Java DefaultDrawLiteSortieImage.drawLiteSortieImage()。

    Args:
        renderer: CardRenderer 实例。
        lite_sortie: LiteSortie 模型。

    Returns:
        PIL Image 对象。
    """
    missions = lite_sortie.missions if lite_sortie.missions else []
    mission_count = len(missions)

    # ---- 动态高度计算 ----
    content_h = (_MISSIONS_START_Y
                 + max(mission_count, 1) * _ROW_H
                 + _STANDING_MAX_H
                 + _FOOTER_OFFSET)
    canvas_h = max(content_h, _MIN_HEIGHT)

    # ---- 字体 ----
    title_font = FontManager.get_text_font(44)
    info_font = FontManager.get_text_font(26)
    mission_font = FontManager.get_text_font(24)
    FontManager.get_text_font(20)

    # ---- 画布 ----
    cb = ImageCombiner(_CANVAS_W, canvas_h, ThemeColor.BG_DARK)

    # ---- 双层边框 ----
    cb.draw_default_double_border()

    # ---- 标题 ----
    cb.set_color(ThemeColor.ACCENT_BLUE).set_font(title_font)
    cb.add_centered_text("执刑官猎杀", _TITLE_Y)

    # ---- 分割线 ----
    cb.draw_content_divider(_DIVIDER_Y, _CONTENT_X, _CONTENT_W)

    # ---- Boss + 结束时间 ----
    current_y = _INFO_START_Y

    boss_name = lite_sortie.boss.display_name if lite_sortie.boss else "未知"
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(info_font)
    cb.add_text(f"Boss: {boss_name}", _CONTENT_X, current_y)

    if lite_sortie.expiry is not None:
        expiry_dt = datetime.fromtimestamp(lite_sortie.expiry.time_millis / 1000, tz=timezone.utc)
        expiry_str = expiry_dt.strftime("%Y-%m-%d %H:%M:%S")
        cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(info_font)
        cb.add_text(f"结束时间: {expiry_str}", _CANVAS_W // 2 - 60, current_y)

    # ---- 任务列表标题 ----
    current_y = _MISSIONS_START_Y - 40
    cb.set_color(ThemeColor.ACCENT_BLUE).set_font(info_font)
    cb.add_text("任务列表:", _CONTENT_X, current_y)

    # ---- 任务列表 ----
    current_y = _MISSIONS_START_Y
    if missions:
        for mission in missions:
            _draw_mission_row(cb, mission, current_y, renderer, mission_font)
            current_y += _ROW_H
    else:
        cb.set_color(ThemeColor.TEXT_MUTED).set_font(mission_font)
        cb.add_text("暂无任务信息", _CONTENT_X + 20, current_y)

    # ---- 看板娘 ----
    draw_standing(cb, max_w=_STANDING_MAX_W, max_h=_STANDING_MAX_H)

    # ---- 底部署名 ----
    cb.draw_card_footer(canvas_h)

    return cb.to_image()


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _draw_mission_row(
    cb: ImageCombiner,
    mission: Mission,
    y: int,
    renderer: CardRenderer,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """绘制单个任务行（带颜色的任务类型 + 节点名）。

    镜像 Java DefaultDrawLiteSortieImage 中 mission 行循环：
      combiner.setColor(mission.getMissionTypeColor())
             .addText("• " + mission.getMissionTypeName() + " - " + mission.getNode(), ...)
    """
    mt = mission.mission_type
    mt_display = mt.display_name if mt else "未知任务"
    mt_color = renderer.resolve_mission_type_color(mt) if mt else ThemeColor.TEXT_SECONDARY
    node = mission.node or "未知节点"

    cb.set_color(mt_color).set_font(font)
    cb.add_text(f"• {mt_display} - {node}", _CONTENT_X + 20, y + 10)
