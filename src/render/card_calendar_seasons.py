"""1999日历卡片渲染器 — 迁移自 Java DefaultDrawKnownCalendarSeasonsImage

采用两列月份网格布局：
  - 居中标题 + 双层装饰边框
  - 季节信息行（当前季节/年份迭代/版本）
  - 每月区域：月份标题 + 每日事件列表（类型着色）
  - 看板娘立绘（跟随日历数据里的季节：春/夏/秋/冬，季节为空用默认）+ 底部署名
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import ImageFont

from ..util.string_utils import path_tail
from .draw_constant import LayoutConstants, ThemeColor
from .font_manager import FontManager
from .image_combiner import ImageCombiner
from .standing import draw_standing, standing_index_for_season
from .text_utils import wrap_text

if TYPE_CHECKING:
    from PIL import Image

    from ..model.world_state import KnownCalendarSeasons
    from .card_renderer import CardRenderer


# ---------------------------------------------------------------------------
# 布局常量
# ---------------------------------------------------------------------------

_CANVAS_W = 1500
_CONTENT_X, _CONTENT_W = LayoutConstants.get_content_bounds(_CANVAS_W)

_MONTHS_PER_ROW = 2
_MONTH_W = 650
_MONTH_GAP = 50
_MONTH_HEADER_H = 50
_MONTH_BODY_OFFSET = 10   # 月份标题与首日之间留白（高度计算与绘制同口径）
_MONTH_FOOTER_H = 20
_DAY_H = 28
_EVENT_H = 26
_EVENT_MAX_W = 580
_COL_GAP_Y = 30           # 同列月份卡之间的纵向间距

_MIN_HEIGHT = 800

_TITLE_Y = 70
_DIVIDER_Y = 138
_INFO_START_Y = 175
_GRID_START_Y = 250
_FOOTER_OFFSET = 55

_STANDING_MAX_W = 310
_STANDING_MAX_H = 420

# 事件类型颜色 — 对齐 Go draw/known_calendar_seasons.go
_EVENT_CHALLENGE_COLOR = (255, 107, 107)   # 红色系 - 任务
_EVENT_REWARD_COLOR = (76, 175, 80)         # 绿色系 - 奖励
_EVENT_UPGRADE_COLOR = (184, 134, 11)       # 金色系 - 加成（原 (85,72,32) 在深色底上几乎不可读）
_SEASON_COLOR = (46, 134, 171)              # #2E86AB - 季节信息

# 月份 → 季节色（对齐 Go calendarSeasonColor）
_SEASON_COLORS = {
    "winter": (0x34, 0x98, 0xDB),
    "spring": (0xE9, 0x1E, 0x8C),
    "summer": (0xFF, 0x98, 0x00),
    "autumn": (0xC0, 0x39, 0x2B),
}


def _season_color(month: int) -> tuple[int, int, int]:
    """月份 → 季节色（12/1-3 冬、4-6 春、7-9 夏、其余秋）。"""
    if month == 12 or month <= 3:
        return _SEASON_COLORS["winter"]
    if month <= 6:
        return _SEASON_COLORS["spring"]
    if month <= 9:
        return _SEASON_COLORS["summer"]
    return _SEASON_COLORS["autumn"]


# ---------------------------------------------------------------------------
# 主渲染函数
# ---------------------------------------------------------------------------

def render_calendar_seasons_card(
    renderer: CardRenderer,
    calendars: list[KnownCalendarSeasons],
) -> Image.Image:
    """绘制1999日历季节信息卡片 — 镜像 Java drawKnownCalendarSeasonsImage()。

    布局为两列「列平衡」：每张月份卡放进当前较矮的一列，避免行网格在月份数为
    奇数时留下大片空白（对齐 Go 的 colEndY 逻辑）。

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

    # ---- 字体 ----
    title_font = FontManager.get_text_font(44)
    info_font = FontManager.get_text_font(28)
    month_title_font = FontManager.get_text_font(26)
    day_font = FontManager.get_text_font(22)
    event_font = FontManager.get_text_font(20)

    # ---- 先建一块临时画布用于量文字（换行宽度与绘制同口径）----
    probe = ImageCombiner(_CANVAS_W, _MIN_HEIGHT, ThemeColor.BG_DARK)
    heights = {
        int(mk): _calc_month_height(probe.draw, month_days_raw[mk], event_font)
        for mk in month_keys
        if isinstance(month_days_raw[mk], list)
    }

    # ---- 列平衡排布 ----
    grid_total_w = _MONTHS_PER_ROW * _MONTH_W + (_MONTHS_PER_ROW - 1) * _MONTH_GAP
    grid_start_x = _CONTENT_X + (_CONTENT_W - grid_total_w) // 2
    col_x = [grid_start_x + i * (_MONTH_W + _MONTH_GAP) for i in range(_MONTHS_PER_ROW)]
    col_y = [_GRID_START_Y] * _MONTHS_PER_ROW

    placements: list[tuple[int, int, int, int]] = []  # (month, x, y, h)
    for mk in month_keys:
        month = int(mk)
        h = heights.get(month)
        if h is None:
            continue
        col = 0 if col_y[0] <= col_y[1] else 1
        placements.append((month, col_x[col], col_y[col], h))
        col_y[col] += h + _COL_GAP_Y

    total_grid_h = (
        max(col_y) - _COL_GAP_Y - _GRID_START_Y if placements else 0
    )
    canvas_h = max(
        _GRID_START_Y + total_grid_h + _STANDING_MAX_H + _FOOTER_OFFSET,
        _MIN_HEIGHT,
    )

    # ---- 画布 ----
    cb = ImageCombiner(_CANVAS_W, canvas_h, ThemeColor.BG_DARK)

    cb.draw_default_double_border()

    # ---- 标题 ----
    cb.set_color(ThemeColor.ACCENT_BLUE).set_font(title_font)
    cb.add_centered_text("1999日历季节信息", _TITLE_Y)

    cb.draw_content_divider(_DIVIDER_Y, _CONTENT_X, _CONTENT_W)

    # ---- 季节基本信息 ----
    _draw_calendar_info(cb, calendar, info_font)

    # ---- 月份卡片 ----
    for month, x, y, h in placements:
        _draw_month_section(
            cb,
            month,
            month_days_raw[month],
            x,
            y,
            h,
            month_title_font,
            day_font,
            event_font,
        )

    # ---- 看板娘（按日历数据里的季节换装，季节为空则用默认立绘）----
    draw_standing(
        cb,
        max_w=_STANDING_MAX_W,
        max_h=_STANDING_MAX_H,
        index=standing_index_for_season(calendar.season),
    )

    # ---- 底部署名 ----
    cb.draw_card_footer(canvas_h)

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


def _calc_month_height(draw, days: list, event_font) -> int:
    """计算单个月份卡所需高度。

    必须与 ``_draw_month_section`` 同口径：事件文本按 ``wrap_text`` 的实际行数计入，
    否则长文本（尤其未翻译的 ``/Lotus/...`` 路径）换行后会撑破卡片、压到下一张上。
    """
    h = _MONTH_HEADER_H + _MONTH_BODY_OFFSET
    for day in days or []:
        h += _DAY_H
        events = getattr(day, "events", None) or []
        if not events:
            h += _EVENT_H
            continue
        for evt in events:
            _, text = _format_event(evt)
            lines = wrap_text(draw, text, _EVENT_MAX_W, event_font) if text else []
            h += max(len(lines), 1) * _EVENT_H
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
    accent = _season_color(month)

    # 背景框 + 顶部季节色装饰条（对齐 Go drawMonthCard）
    cb.set_color(ThemeColor.BG_CARD)
    cb.draw_rounded_rect(start_x, start_y, _MONTH_W, section_h, radius=15)
    cb.set_color(accent)
    cb.draw_rounded_rect(
        start_x + 15, start_y + 2, _MONTH_W - 30, 5, radius=2
    )
    cb.set_color(ThemeColor.DIVIDER)
    cb.draw_rounded_rect(start_x, start_y, _MONTH_W, section_h, radius=15, outline=ThemeColor.DIVIDER, stroke_width=2)

    # 月份标题（按季节着色）
    cb.set_color(accent).set_font(title_font)
    cb.add_text(f"{month}月", start_x + 20, start_y + 32)

    # 每日事件
    current_y = start_y + _MONTH_HEADER_H + _MONTH_BODY_OFFSET
    for day in days or []:
        day_num = day.day if day.day is not None else "?"
        month_num = day.month if day.month is not None else month
        events = day.events or []

        # 日期标注
        cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(day_font)
        cb.add_text(f"{month_num}月{day_num}日", start_x + 20, current_y + 2)
        current_y += _DAY_H

        # 事件列表
        if events:
            for evt in events:
                color, text = _format_event(evt)
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


def _format_event(evt) -> tuple[tuple[int, int, int], str]:
    """根据事件类型格式化事件文本和颜色。

    事件类型是枚举（成员名 ``CET_CHALLENGE``，值「任务」），
    API 也可能直接给成员名，所以两种写法都认。
    未翻译的路径取尾段（对齐 Go ``PathTail``），避免整条 ``/Lotus/...`` 画进卡片。
    """
    evt_type = getattr(evt, "type", None)
    type_key = getattr(evt_type, "name", None) or str(evt_type or "")

    if type_key in ("CET_CHALLENGE", "任务"):
        name = path_tail(evt.challenge or "")
        return _EVENT_CHALLENGE_COLOR, f"[任务] {name}" if name else ""
    if type_key in ("CET_REWARD", "奖励"):
        reward = path_tail(evt.reward or "")
        return _EVENT_REWARD_COLOR, f"[奖励] {reward}" if reward else ""
    if type_key in ("CET_UPGRADE", "加成"):
        upgrade = path_tail(evt.upgrade or "")
        return _EVENT_UPGRADE_COLOR, f"[加成] {upgrade}" if upgrade else ""
    return ThemeColor.TEXT_MUTED, ""
