"""裂隙卡片渲染器

采用两列卡片网格布局，镜像 Java DefaultDrawActiveMission.java：
  - 居中标题 + 动态切换（虚空裂隙 / 钢铁裂隙 / 虚空风暴）
  - 每张卡片顶部 tier 颜色强调条 + 三行信息
  - 双层边框 + 看板娘立绘（奇数填补右列 / 偶数置于底部）+ 底部署名
"""
from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING

from PIL import ImageFont

from .draw_constant import LayoutConstants, ThemeColor, hex_to_rgb
from .font_manager import FontManager
from .image_combiner import ImageCombiner
from .standing import draw_standing_at

if TYPE_CHECKING:
    from PIL import Image

    from ..model.world_state import ActiveMission
    from ..wenum.world_state import VoidEnum
    from .card_renderer import CardRenderer


# ---------------------------------------------------------------------------
# 布局常量
# ---------------------------------------------------------------------------

_CANVAS_W = 1200
_CONTENT_X, _CONTENT_W = LayoutConstants.get_content_bounds(_CANVAS_W)

_COLS = 2                          # 每行列数
_COL_GAP = 20                      # 列间距
_CARD_W = (_CONTENT_W - _COL_GAP) // _COLS  # 530
_CARD_H = 160                      # 卡片高度
_CARD_RADIUS = 14
_CARD_PAD = 20                     # 卡片内边距
_ROW_GAP = 16                      # 行间距
_ACCENT_STRIP_H = 4                # 顶部强调条高度

# 列 X 坐标
_COL_X = (
    _CONTENT_X,                     # 左列 = 60
    _CONTENT_X + _CARD_W + _COL_GAP,  # 右列 = 610
)

_TITLE_Y = 60
_CONTENT_START_Y = 175
_FOOTER_OFFSET = 50

# 看板娘尺寸
_STANDING_ODD_W = 310
_STANDING_ODD_H = 360
_STANDING_EVEN_W = 260
_STANDING_EVEN_H = 390


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _get_time_color(time_left: str) -> tuple[int, int, int]:
    """根据剩余时间返回颜色 — 镜像 Java getTimeColor()。

    含小时 → 绿色；10-59 分钟 → 黄色；<10 分钟 → 红色。
    """
    if not time_left:
        return ThemeColor.TIME_LOW
    if "h" in time_left.lower():
        return ThemeColor.TIME_HIGH
    if "m" in time_left.lower():
        minutes = int(re.sub(r"\D", "", time_left) or "60")
        return ThemeColor.TIME_LOW if minutes < 10 else ThemeColor.TIME_MEDIUM
    return ThemeColor.TIME_LOW


def _lighten_color(rgb: tuple[int, int, int], factor: float = 0.45) -> tuple[int, int, int]:
    """将 RGB 颜色往白色方向提亮，用于暗色背景上的文字可读性。

    factor=0 不变，factor=1 完全变白。
    """
    return (
        int(rgb[0] + (255 - rgb[0]) * factor),
        int(rgb[1] + (255 - rgb[1]) * factor),
        int(rgb[2] + (255 - rgb[2]) * factor),
    )


# VoidEnum 英文名映射（VoidEnum 仅有 display_name + color，无 en_name）
_VOID_EN_NAMES = {
    "VoidT1": "Lith",
    "VoidT2": "Meso",
    "VoidT3": "Neo",
    "VoidT4": "Axi",
    "VoidT5": "Requiem",
    "VoidT6": "Omnia",
}


def _build_tier_display(modifier: VoidEnum) -> str:
    """构建 tier 显示文本，如 '古纪 Lith'。"""
    en = _VOID_EN_NAMES.get(modifier.name, "")
    return f"{modifier.display_name} {en}" if en else modifier.display_name


def _build_title(fissures: list[ActiveMission]) -> tuple[str, tuple[int, int, int]]:
    """根据数据确定标题文字和颜色。

    优先取第一条的 void_storms / hard 标志，镜像 Java 三元标题逻辑。
    """
    if not fissures:
        return "虚空裂隙", ThemeColor.ACCENT_BLUE
    first = fissures[0]
    if first.void_storms:
        return "虚空风暴", ThemeColor.ACCENT_BLUE
    if first.hard:
        return "钢铁裂隙", ThemeColor.DANGER
    return "虚空裂隙", ThemeColor.ACCENT_BLUE


def _draw_one_fissure_card(
    cb: ImageCombiner,
    mission: ActiveMission,
    card_x: int,
    card_y: int,
    renderer: CardRenderer,
    tier_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    body_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    time_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    location_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """绘制单张裂隙卡片。"""
    inner_x = card_x + _CARD_PAD
    inner_w = _CARD_W - _CARD_PAD * 2

    modifier = mission.modifier

    # 卡片圆角背景
    cb.set_color(ThemeColor.BG_CARD)
    cb.draw_rounded_rect(card_x, card_y, _CARD_W, _CARD_H, radius=_CARD_RADIUS)

    # 顶部 tier 颜色强调条（左右内缩 radius，贴合圆角）
    if modifier is not None:
        tier_rgb = hex_to_rgb(modifier.color)
        cb.set_color(tier_rgb)
        cb.fill_rect(card_x + _CARD_RADIUS, card_y + 2, _CARD_W - 2 * _CARD_RADIUS, _ACCENT_STRIP_H)

    # ---- 行 1: tier 名称（左） + 剩余时间（右） ----
    tier_text = _build_tier_display(modifier) if modifier else "未知等级"
    tier_color = _lighten_color(hex_to_rgb(modifier.color)) if modifier else ThemeColor.TEXT_SECONDARY
    cb.set_color(tier_color).set_font(tier_font)
    cb.add_text( tier_text, inner_x, card_y + 32)

    time_left = mission.time_left or "未知"
    time_color = _get_time_color(time_left)
    cb.set_color(time_color).set_font(time_font)
    time_w = cb.get_string_width(time_left)
    cb.add_text( time_left, inner_x + inner_w - time_w, card_y + 33)

    # ---- 行 2: 任务类型 + 派系图标 + 派系名称（左右居中） ----
    row2_y = card_y + 72

    # 收集要绘制的片段及各自颜色/字体
    fragments: list[tuple[str, tuple[int, int, int], ImageFont.FreeTypeFont | ImageFont.ImageFont]] = []

    mt = mission.mission_type
    mt_display = mt.display_name if mt is not None else "未知"
    mt_color = renderer.resolve_mission_type_color(mt) if mt is not None else ThemeColor.TEXT_SECONDARY
    fragments.append((mt_display, mt_color, body_font))

    faction = mission.faction
    if faction is not None:
        icon, faction_color = renderer.resolve_faction_icon_and_color(faction)
        if icon and renderer.font_wf_icon:
            fragments.append((icon, faction_color, renderer.font_wf_icon))
        fragments.append((faction.display_name, faction_color, body_font))

    # 计算整行总宽度，用于居中
    total_row2_w = 0
    for text, _, font in fragments:
        saved = cb.current_font
        cb.set_font(font)
        total_row2_w += cb.get_string_width(text)
        cb.set_font(saved)
    gap = 8 if len(fragments) > 1 else 0
    total_row2_w += gap * (len(fragments) - 1)

    cursor_x = inner_x + (inner_w - total_row2_w) // 2
    for text, color, font in fragments:
        cb.set_color(color).set_font(font)
        cb.add_text( text, cursor_x, row2_y + 3)
        cursor_x += cb.get_string_width(text) + gap

    # ---- 行 3: 节点位置 ----
    node = mission.node or "未知节点"
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(location_font)
    cb.add_text( node, inner_x, card_y + 118)


# ---------------------------------------------------------------------------
# 主渲染函数
# ---------------------------------------------------------------------------

def draw_fissure_card(
    renderer: CardRenderer,
    fissures: list[ActiveMission],
) -> Image.Image:
    """绘制裂隙信息卡片 — 两列卡片网格 + 双层边框 + 看板娘 + 底部署名。

    Args:
        renderer: CardRenderer 实例。
        fissures: ActiveMission 列表（已由 Service 翻译并排序）。

    Returns:
        PIL Image 对象。
    """
    if not fissures:
        return renderer.create_text_image("当前没有活跃的裂隙", 800, 120)

    # ---- 字体 ----
    title_font = FontManager.get_text_font(56)
    tier_font = FontManager.get_text_font(30)
    body_font = FontManager.get_text_font(26)
    time_font = FontManager.get_text_font(24)
    location_font = FontManager.get_text_font(22)
    FontManager.get_text_font(20)

    # ---- 布局计算 ----
    n = len(fissures)
    rows = math.ceil(n / _COLS)
    cards_h = rows * _CARD_H + (rows - 1) * _ROW_GAP
    is_odd = n % _COLS != 0
    last_row_y = _CONTENT_START_Y + (rows - 1) * (_CARD_H + _ROW_GAP)

    # ---- 画布高度（看板娘位置不同，高度不同） ----
    if is_odd:
        standing_h = _STANDING_ODD_H
        content_end = _CONTENT_START_Y + cards_h
        canvas_h = max(content_end, last_row_y + standing_h + _FOOTER_OFFSET + 10)
    else:
        standing_h = _STANDING_EVEN_H
        content_end = _CONTENT_START_Y + cards_h
        canvas_h = content_end + standing_h + _FOOTER_OFFSET + 20

    # ---- 画布 ----
    cb = ImageCombiner(_CANVAS_W, canvas_h, ThemeColor.BG_DARK)

    # ---- 双层边框 ----
    cb.draw_default_double_border()

    # ---- 标题 ----
    title_text, title_color = _build_title(fissures)
    cb.set_color(title_color).set_font(title_font)
    cb.add_centered_text(title_text, _TITLE_Y)

    # ---- 分割线 ----
    cb.draw_content_divider(_TITLE_Y + 68, _CONTENT_X, _CONTENT_W)

    # ---- 裂隙卡片（两列网格） ----
    for i, fissure in enumerate(fissures):
        row = i // _COLS
        col = i % _COLS
        card_x = _COL_X[col]
        card_y = _CONTENT_START_Y + row * (_CARD_H + _ROW_GAP)
        _draw_one_fissure_card(
            cb, fissure, card_x, card_y, renderer,
            tier_font, body_font, time_font, location_font,
        )

    # ---- 看板娘 ----
    if is_odd:
        standing_x = _COL_X[1] + (_CARD_W - _STANDING_ODD_W) // 2
        draw_standing_at(cb, standing_x, last_row_y,
                         _STANDING_ODD_W, _STANDING_ODD_H)
    else:
        standing_x = _CONTENT_X + _CONTENT_W - _STANDING_EVEN_W - 20
        draw_standing_at(cb, standing_x, content_end + 10,
                         _STANDING_EVEN_W, _STANDING_EVEN_H)

    # ---- 底部署名 ----
    cb.draw_card_footer(canvas_h, 50)

    return cb.to_image()
