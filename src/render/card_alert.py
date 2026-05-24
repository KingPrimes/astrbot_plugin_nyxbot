"""警报卡片渲染器

采用 HTML 卡片列表式布局：
  - 居中标题 + 双层装饰边框
  - 横板两列并排，每条警报为独立卡片（圆角背景 + 徽章式标签）
  - 奇数条：看板娘填补右侧空位
  - 偶数条：看板娘置于底部右侧，不遮挡数据
  - Footer 署名
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PIL import Image, ImageFont

from .draw_constant import DrawConstant, ThemeColor
from .font_manager import FontManager
from .image_combiner import ImageCombiner
from .standing import draw_standing_at

if TYPE_CHECKING:
    from ..model.world_state import Alert
    from .card_renderer import CardRenderer


# ---------------------------------------------------------------------------
# 布局常量
# ---------------------------------------------------------------------------

_CANVAS_W = 1200
_MARGIN = 40                       # 双层边框外边距
_CONTENT_PAD = 20                  # 边框内缩进
_CONTENT_X = _MARGIN + _CONTENT_PAD  # 内容区起始 X = 60
_CONTENT_W = _CANVAS_W - 2 * _CONTENT_X  # 980

_COLS = 2                          # 每行列数
_COL_GAP = 20                      # 列间距
_CARD_W = (_CONTENT_W - _COL_GAP) // _COLS  # 480

# 列 X 坐标
_COL_X = (
    _CONTENT_X,                     # 左列 = 60
    _CONTENT_X + _CARD_W + _COL_GAP,  # 右列 = 560
)

_TITLE_Y = 70
_CONTENT_START_Y = 170

# 每条警报卡片
_CARD_H = 150
_ROW_GAP = 16                      # 行间距
_CARD_PAD = 20                     # 卡片内边距
_CARD_RADIUS = 14

# 看板娘 — 奇数（填补右列空位）/ 偶数（底部右侧）
_STANDING_ODD_W = 310
_STANDING_ODD_H = 360
_STANDING_EVEN_W = 260
_STANDING_EVEN_H = 390

_FOOTER_OFFSET = 60               # 署名距底部距离


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

def _build_reward_text(alert: Alert) -> str:
    """构建单行奖励文本 — 对应 Java 的 credits+"星币" + items。"""
    mi = alert.mission_info
    if mi is None:
        return ""
    reward = mi.mission_reward
    if reward is None:
        return ""

    segments: list[str] = []

    if reward.credits and reward.credits > 0:
        segments.append(f"{reward.credits}星币")

    if reward.counted_items:
        item_texts: list[str] = []
        for item in reward.counted_items[:5]:
            if item.count > 1:
                item_texts.append(f"{item.name}×{item.count}")
            else:
                item_texts.append(item.name)
        segments.append("  ".join(item_texts))

    return "  ".join(segments) if segments else ""


def _draw_one_card(
    cb: ImageCombiner,
    alert: Alert,
    card_x: int,
    card_y: int,
    renderer: CardRenderer,
    location_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    badge_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    body_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    time_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """绘制单张警报卡片。"""
    mi = alert.mission_info
    inner_x = card_x + _CARD_PAD
    inner_w = _CARD_W - _CARD_PAD * 2

    # 卡片背景
    cb.set_color(ThemeColor.BG_CARD)
    cb.draw_rounded_rect(card_x, card_y, _CARD_W, _CARD_H, radius=_CARD_RADIUS)

    # 行 1: 地点（左） + 剩余时间（右）
    location = mi.location if mi and mi.location else "未知节点"
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(location_font)
    cb.add_text(location, inner_x, card_y + 20)

    eta = alert.time_left or "未知"
    cb.set_color(ThemeColor.WARNING).set_font(time_font)
    eta_w = cb.get_string_width(eta)
    cb.add_text(eta, inner_x + inner_w - eta_w, card_y + 22)

    # 行 2: 任务类型 + 派系 + 奖励（颜色直接作用于文字，无背景方框）
    badge_y = card_y + 64
    cursor_x = inner_x

    # 任务类型（有色文字）
    if mi and mi.mission_type:
        mt_display = mi.mission_type.display_name
        mt_color = renderer.resolve_mission_type_color(mi.mission_type)
    else:
        mt_display = "未知"
        mt_color = ThemeColor.TEXT_SECONDARY

    cb.set_color(mt_color).set_font(badge_font)
    cb.add_text(mt_display, cursor_x, badge_y + 3)
    cursor_x += cb.get_string_width(mt_display) + 10

    # 派系（有色文字）
    if mi and mi.faction:
        faction_name = mi.faction.display_name
        _, faction_color = renderer.resolve_faction_icon_and_color(mi.faction)
    else:
        faction_name = "未知"
        faction_color = ThemeColor.TEXT_SECONDARY

    cb.set_color(faction_color).set_font(badge_font)
    cb.add_text(faction_name, cursor_x, badge_y + 3)
    cursor_x += cb.get_string_width(faction_name) + 14

    # 奖励文字
    reward_text = _build_reward_text(alert)
    if reward_text:
        cb.set_color(ThemeColor.ACCENT_GOLD).set_font(body_font)
        max_reward_w = inner_x + inner_w - cursor_x - 6
        reward_w = cb.get_string_width(reward_text)
        if reward_w > max_reward_w:
            while reward_w > max_reward_w and len(reward_text) > 3:
                reward_text = reward_text[:-4] + ".."
                reward_w = cb.get_string_width(reward_text)
        cb.add_text(reward_text, cursor_x, badge_y + 1)


# ---------------------------------------------------------------------------
# 主渲染函数
# ---------------------------------------------------------------------------

def render_alert_card(renderer: CardRenderer, alerts: list[Alert]) -> Image.Image:
    """绘制警报信息卡片 — 两列并排，看板娘位置按奇偶自适应。

    Args:
        renderer: CardRenderer 实例。
        alerts: Alert 模型列表。

    Returns:
        PIL Image 对象。
    """
    if not alerts:
        return renderer.create_text_image("当前没有活跃的警报", 800, 120)

    # ---- 字体 ----
    title_font = FontManager.get_text_font(56)
    location_font = FontManager.get_text_font(28)
    badge_font = FontManager.get_text_font(22)
    body_font = FontManager.get_text_font(24)
    time_font = FontManager.get_text_font(20)
    footer_font = FontManager.get_text_font(20)

    # ---- 布局计算 ----
    n = len(alerts)
    rows = math.ceil(n / _COLS)
    cards_h = rows * _CARD_H + (rows - 1) * _ROW_GAP
    is_odd = n % _COLS != 0
    last_row_y = _CONTENT_START_Y + (rows - 1) * (_CARD_H + _ROW_GAP)

    # ---- 画布高度（看板娘位置不同，高度不同） ----
    if is_odd:
        # 看板娘填补右列空位，从最后一行 Y 开始向下延伸
        standing_h = _STANDING_ODD_H
        content_end = _CONTENT_START_Y + cards_h
        canvas_h = max(content_end, last_row_y + standing_h + _FOOTER_OFFSET + 10)
    else:
        # 看板娘在卡片下方，右侧
        standing_h = _STANDING_EVEN_H
        content_end = _CONTENT_START_Y + cards_h
        canvas_h = content_end + standing_h + _FOOTER_OFFSET + 20

    # ---- 画布 ----
    cb = ImageCombiner(_CANVAS_W, canvas_h, ThemeColor.BG_DARK)

    # ---- 双层装饰边框 ----
    cb.draw_double_border(
        border_padding=16,
        border_color_outer=ThemeColor.TABLE_BORDER,
        border_color_inner=ThemeColor.DIVIDER,
        stroke=3,
    )

    # ---- 标题 ----
    cb.set_color(ThemeColor.ACCENT_BLUE).set_font(title_font)
    cb.add_centered_text("警报", _TITLE_Y)

    # ---- 分割线（标题下方，与卡片区域等宽） ----
    cb.set_color(ThemeColor.DIVIDER)
    cb.draw_line(_CONTENT_X, _TITLE_Y + 68, _CONTENT_X + _CONTENT_W, _TITLE_Y + 68, width=1)

    # ---- 警报卡片（两列网格） ----
    for i, alert in enumerate(alerts):
        row = i // _COLS
        col = i % _COLS
        card_x = _COL_X[col]
        card_y = _CONTENT_START_Y + row * (_CARD_H + _ROW_GAP)
        _draw_one_card(cb, alert, card_x, card_y, renderer,
                       location_font, badge_font, body_font, time_font)

    # ---- 看板娘 ----
    if is_odd:
        # 奇数：填补最后一行右侧空位
        standing_x = _COL_X[1] + (_CARD_W - _STANDING_ODD_W) // 2
        draw_standing_at(cb, standing_x, last_row_y,
                         _STANDING_ODD_W, _STANDING_ODD_H)
    else:
        # 偶数：卡片下方偏右，不遮挡左侧卡片投影
        standing_x = _CONTENT_X + _CONTENT_W - _STANDING_EVEN_W - 20
        draw_standing_at(cb, standing_x, content_end + 10,
                         _STANDING_EVEN_W, _STANDING_EVEN_H)

    # ---- Footer（距底部固定 55px） ----
    cb.set_color(ThemeColor.TEXT_MUTED).set_font(footer_font)
    cb.add_centered_text(DrawConstant.FOOTER_TEXT, canvas_h - _FOOTER_OFFSET)

    return cb.to_image()


# ---------------------------------------------------------------------------
