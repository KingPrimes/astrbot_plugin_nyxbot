"""1999日历卡片渲染器 — 迁移自 Java DefaultDrawKnownCalendarSeasonsImage

采用两列月份网格布局：
  - 居中标题 + 双层装饰边框
  - 季节信息行（当前季节/年份迭代/版本）
  - 每月区域：月份标题 + 每日事件列表（类型着色）
  - 看板娘立绘 + 底部署名
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PIL import ImageFont

from .draw_constant import DrawConstant, ThemeColor
from .font_manager import FontManager
from .image_combiner import ImageCombiner
from .standing import draw_standing
from .text_utils import wrap_text

if TYPE_CHECKING:
    from PIL import Image

    from ..model.world_state import KnownCalendarSeasons
    from .card_renderer import CardRenderer


# ---------------------------------------------------------------------------
# 布局常量
# ---------------------------------------------------------------------------

_CANVAS_W = 1500
_MARGIN = 40
_CONTENT_PAD = 20
_CONTENT_X = _MARGIN + _CONTENT_PAD
_CONTENT_W = _CANVAS_W - 2 * _CONTENT_X

_MONTHS_PER_ROW = 2
_MONTH_W = 650
_MONTH_GAP = 50
_MONTH_HEADER_H = 50
_MONTH_FOOTER_H = 20
_DAY_H = 28
_EVENT_H = 26
_EVENT_MAX_W = 580

_MIN_HEIGHT = 800

_TITLE_Y = 70
_DIVIDER_Y = 138
_INFO_START_Y = 175
_GRID_START_Y = 250
_FOOTER_OFFSET = 55

_STANDING_MAX_W = 310
_STANDING_MAX_H = 420

# 事件类型颜色 — 镜像 Java
_EVENT_CHALLENGE_COLOR = (255, 107, 107)   # 红色系 - 任务
_EVENT_REWARD_COLOR = (76, 175, 80)         # 绿色系 - 奖励
_EVENT_UPGRADE_COLOR = (85, 72, 32)         # 橙色系 - 加成
_SEASON_COLOR = (46, 134, 171)              # #2E86AB - 季节信息


# ---------------------------------------------------------------------------
# 主渲染函数
# ---------------------------------------------------------------------------

def render_calendar_seasons_card(
    renderer: CardRenderer,
    calendars: list[KnownCalendarSeasons],
) -> Image.Image:
    """绘制1999日历季节信息卡片 — 镜像 Java drawKnownCalendarSeasonsImage()。

    Args:
        renderer: CardRenderer 实例。
        calendars: KnownCalendarSeasons 模型列表（通常仅一个元素）。

    Returns:
        PIL Image 对象。
    """
    if not calendars:
        return renderer.create_text_image("当前没有1999日历数据", 800, 120)

    calendar = calendars[0]

    # 解析 month_days 数据
    month_days_raw = calendar.month_days or {}
    month_keys = sorted(month_days_raw.keys(), key=lambda k: int(k))

    # ---- 计算每行最大高度 ----
    rows = math.ceil(len(month_keys) / _MONTHS_PER_ROW)
    row_heights: list[int] = []
    for row in range(rows):
        max_h = 0
        for col in range(_MONTHS_PER_ROW):
            idx = row * _MONTHS_PER_ROW + col
            if idx >= len(month_keys):
                break
            days = month_days_raw[month_keys[idx]]
            if isinstance(days, list):
                mh = _calc_month_height(days)
                max_h = max(max_h, mh)
        row_heights.append(max(_MONTH_HEADER_H + _DAY_H + _MONTH_FOOTER_H, max_h))

    total_grid_h = sum(row_heights) + (rows - 1) * 30  # 30px 行间距

    canvas_h = max(_GRID_START_Y + total_grid_h + _STANDING_MAX_H + _FOOTER_OFFSET, _MIN_HEIGHT)

    # ---- 字体 ----
    title_font = FontManager.get_text_font(44)
    info_font = FontManager.get_text_font(28)
    month_title_font = FontManager.get_text_font(26)
    day_font = FontManager.get_text_font(22)
    event_font = FontManager.get_text_font(20)
    footer_font = FontManager.get_text_font(20)

    # ---- 画布 ----
    cb = ImageCombiner(_CANVAS_W, canvas_h, ThemeColor.BG_DARK)

    cb.draw_double_border(
        border_padding=16,
        border_color_outer=ThemeColor.TABLE_BORDER,
        border_color_inner=ThemeColor.DIVIDER,
        stroke=3,
    )

    # ---- 标题 ----
    cb.set_color(ThemeColor.ACCENT_BLUE).set_font(title_font)
    cb.add_centered_text("1999日历季节信息", _TITLE_Y)

    cb.set_color(ThemeColor.DIVIDER)
    cb.draw_line(_CONTENT_X, _DIVIDER_Y, _CONTENT_X + _CONTENT_W, _DIVIDER_Y, width=1)

    # ---- 季节基本信息 ----
    _draw_calendar_info(cb, calendar, info_font)

    # ---- 月份网格 ----
    grid_total_w = _MONTHS_PER_ROW * _MONTH_W + (_MONTHS_PER_ROW - 1) * _MONTH_GAP
    grid_start_x = _CONTENT_X + (_CONTENT_W - grid_total_w) // 2

    current_y = _GRID_START_Y
    for row in range(rows):
        for col in range(_MONTHS_PER_ROW):
            idx = row * _MONTHS_PER_ROW + col
            if idx >= len(month_keys):
                break
            month_key = month_keys[idx]
            days = month_days_raw[month_key]
            month_x = grid_start_x + col * (_MONTH_W + _MONTH_GAP)
            if isinstance(days, list):
                _draw_month_section(cb, int(month_key), days, month_x, current_y,
                                   row_heights[row], month_title_font, day_font, event_font)

        current_y += row_heights[row] + 30

    # ---- 看板娘 ----
    draw_standing(cb, max_w=_STANDING_MAX_W, max_h=_STANDING_MAX_H)

    # ---- 底部署名 ----
    cb.set_color(ThemeColor.TEXT_MUTED).set_font(footer_font)
    cb.add_centered_text(DrawConstant.FOOTER_TEXT, canvas_h - _FOOTER_OFFSET)

    return cb.to_image()


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _draw_calendar_info(
    cb: ImageCombiner,
    calendar: KnownCalendarSeasons,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """绘制季节基本信息行。"""
    season_text = f"当前季节: {calendar.season.value if calendar.season else '未知'}"
    year_text = f"年份迭代: 第{calendar.year_iteration or '未知'}次"
    version_text = f"版本: {calendar.version or '未知'}"

    cb.set_color(_SEASON_COLOR).set_font(font)
    cb.add_text(season_text, _CONTENT_X + 300, _INFO_START_Y)
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(font)
    cb.add_text(year_text, _CONTENT_X + 600, _INFO_START_Y)
    cb.add_text(version_text, _CONTENT_X + 900, _INFO_START_Y)


def _calc_month_height(days: list) -> int:
    """计算单个月份区域所需高度。"""
    h = _MONTH_HEADER_H
    for day in days:
        if not isinstance(day, dict):
            continue
        events = day.get("events", []) or []
        num_events = max(len(events), 1)
        h += _DAY_H + num_events * (_EVENT_H + 4)
    h += _MONTH_FOOTER_H
    return max(h, _MONTH_HEADER_H + _DAY_H + _MONTH_FOOTER_H)


def _draw_month_section(
    cb: ImageCombiner,
    month: int,
    days: list,
    start_x: int,
    start_y: int,
    section_h: int,
    title_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    day_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    event_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """绘制单个月份区域（背景框 + 标题 + 每日事件）。"""
    # 背景框
    cb.set_color(ThemeColor.BG_CARD)
    cb.draw_rounded_rect(start_x, start_y, _MONTH_W, section_h, radius=15)
    cb.set_color(ThemeColor.DIVIDER)
    cb.draw_rounded_rect(start_x, start_y, _MONTH_W, section_h, radius=15, outline=ThemeColor.DIVIDER, stroke_width=2)

    # 月份标题
    cb.set_color(_SEASON_COLOR).set_font(title_font)
    cb.add_text(f"{month}月", start_x + 20, start_y + 32)

    # 每日事件
    current_y = start_y + _MONTH_HEADER_H + 10
    for day in days:
        if not isinstance(day, dict):
            continue
        day_num = day.get("day", "?")
        month_num = day.get("month", month)
        events = day.get("events", []) or []

        # 日期标注
        cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(day_font)
        cb.add_text(f"{month_num}月{day_num}日", start_x + 20, current_y + 2)
        current_y += _DAY_H

        # 事件列表
        if events:
            for evt in events:
                if not isinstance(evt, dict):
                    continue
                evt_type = evt.get("type", "")
                color, text = _format_event(evt, evt_type)
                if text:
                    # 自动换行
                    lines = wrap_text(cb.draw, text, _EVENT_MAX_W, event_font)
                    cb.set_color(color).set_font(event_font)
                    for line in lines:
                        cb.add_text(line, start_x + 40, current_y)
                        current_y += _EVENT_H
                else:
                    current_y += _EVENT_H
        else:
            current_y += _EVENT_H


def _format_event(evt: dict, evt_type: str) -> tuple[tuple[int, int, int], str]:
    """根据事件类型格式化事件文本和颜色。"""
    if evt_type == "CET_CHALLENGE":
        info = evt.get("challengeInfo", {}) or {}
        challenge_name = info.get("challenge", evt.get("challenge", ""))
        return _EVENT_CHALLENGE_COLOR, f"[任务] {challenge_name}" if challenge_name else ""
    elif evt_type == "CET_REWARD":
        reward = evt.get("reward", "")
        return _EVENT_REWARD_COLOR, f"[奖励] {reward}" if reward else ""
    elif evt_type == "CET_UPGRADE":
        info = evt.get("upgradeInfo", {}) or {}
        upgrade = info.get("upgrade", evt.get("upgrade", ""))
        return _EVENT_UPGRADE_COLOR, f"[加成] {upgrade}" if upgrade else ""
    else:
        return ThemeColor.TEXT_MUTED, str(evt)
