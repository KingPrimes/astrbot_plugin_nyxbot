"""1999 日历卡片渲染器 — 迁移自 Java DefaultDrawKnownCalendarSeasonsImage

版式：页头 + 信息条（当前季节 / 年份迭代 / 版本）+ 两列「列平衡」月份卡
+ 看板娘（跟随日历季节换装）+ 署名。

每张月份卡的高度由「日期数 + 事件换行行数」实时算出，不再固定 `_MONTH_W/H`。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..util.string_utils import path_tail
from . import card_frame as frame
from . import components as C
from .card_size import CardSpec, ChipsBlock, CustomBlock, measure_card_size
from .design import FONT, SPACE, adapt_color, font
from .theme import current_theme

if TYPE_CHECKING:
    from PIL import Image

    from ..model.world_state import KnownCalendarSeasons
    from .card_renderer import CardRenderer

#: 月份 → 季节色（12/1-3 冬、4-6 春、7-9 夏、其余秋）。
_SEASON_COLORS = {
    "winter": "#3498DB",
    "spring": "#E91E8C",
    "summer": "#FF9800",
    "autumn": "#C0392B",
}

#: 事件类型 → 语义色（按主题校正）。
_EVENT_COLORS = {
    "challenge": "#FF6B6B",
    "reward": "#4CAF50",
    "upgrade": "#B8860B",
}

#: 布局口径（绘制与测高共用）。
_MONTH_PAD = SPACE["lg"]
_MONTH_MIN_W = 360
_MONTH_MAX_W = 560
_EVENT_INDENT = SPACE["md"]
_EVENT_LINE_H = FONT["xs"] + SPACE["xs"]
_DAY_LINE_H = FONT["sm"] + SPACE["xs"]


def _season_color(month: int, theme) -> tuple[int, int, int]:
    if month == 12 or month <= 3:
        key = "winter"
    elif month <= 6:
        key = "spring"
    elif month <= 9:
        key = "summer"
    else:
        key = "autumn"
    return adapt_color(_SEASON_COLORS[key], theme)


def _format_event(evt, theme) -> tuple[tuple[int, int, int], str]:
    """事件文本 + 颜色；未翻译的路径取尾段（对齐 Go PathTail）。"""
    evt_type = getattr(evt, "type", None)
    type_key = getattr(evt_type, "name", None) or str(evt_type or "")

    if type_key in ("CET_CHALLENGE", "任务"):
        name = path_tail(evt.challenge or "")
        return adapt_color(_EVENT_COLORS["challenge"], theme), f"[任务] {name}" if name else ""
    if type_key in ("CET_REWARD", "奖励"):
        reward = path_tail(evt.reward or "")
        return adapt_color(_EVENT_COLORS["reward"], theme), f"[奖励] {reward}" if reward else ""
    if type_key in ("CET_UPGRADE", "加成"):
        upgrade = path_tail(evt.upgrade or "")
        return adapt_color(_EVENT_COLORS["upgrade"], theme), f"[加成] {upgrade}" if upgrade else ""
    return theme.palette.text_dim, ""


def _month_layout(month: int, days: list, event_w: int, theme) -> tuple[int, list[list]]:
    """算出单月卡高度与逐日绘制行：[(day_label, [(color, line), ...]), ...]。"""
    rows: list[list] = []
    height = _MONTH_PAD * 2 + FONT["md"] + SPACE["md"]

    for day in days or []:
        day_num = getattr(day, "day", None)
        month_num = getattr(day, "month", None) or month
        label = f"{month_num}月{day_num if day_num is not None else '?'}日"
        entries: list[tuple[tuple[int, int, int], str]] = []
        for evt in getattr(day, "events", None) or []:
            color, text = _format_event(evt, theme)
            if not text:
                continue
            for line in C.wrap_lines(text, event_w, font("xs"), max_lines=3):
                entries.append((color, line))
        if not entries:
            entries.append((theme.palette.text_dim, "—"))
        rows.append([label, entries])
        height += _DAY_LINE_H + len(entries) * _EVENT_LINE_H

    return height, rows


def _draw_month(page, month: int, rows: list[list], x: int, y: int, w: int, h: int) -> None:
    theme = page.theme
    palette = page.palette
    cb = page.cb
    accent = _season_color(month, theme)

    C.draw_grid_card(page, x, y, w, h)
    cb.set_color(accent)
    cb.draw_rounded_rect(x + 15, y + 2, w - 30, 4, radius=2, fill=accent)

    cb.set_color(accent).set_font(font("md", bold=True))
    cb.add_text(f"{month}月", x + _MONTH_PAD, y + _MONTH_PAD)

    cursor = y + _MONTH_PAD + FONT["md"] + SPACE["md"]
    for label, entries in rows:
        cb.set_color(palette.text).set_font(font("sm"))
        cb.add_text(label, x + _MONTH_PAD, cursor)
        cursor += _DAY_LINE_H

        for color, line in entries:
            cb.set_color(color).set_font(font("xs"))
            cb.add_text(line, x + _MONTH_PAD + _EVENT_INDENT, cursor)
            cursor += _EVENT_LINE_H


def render_calendar_seasons_card(
    renderer: CardRenderer,
    calendars: list[KnownCalendarSeasons],
) -> Image.Image:
    """绘制 1999 日历季节信息卡片。

    Args:
        renderer: CardRenderer 实例（保留参数以兼容渲染入口）。
        calendars: KnownCalendarSeasons 模型列表（通常仅一个元素）。
    """
    if not calendars:
        return renderer.create_text_image("当前没有1999日历数据", 800, 120)

    theme = current_theme()
    calendar = calendars[0]

    month_days_raw = calendar.month_days or {}
    month_keys = sorted(month_days_raw.keys(), key=lambda key: int(key))

    # ---- 卡片宽度：由最长事件文本决定（夹在 360~560）----
    event_font = font("xs")
    longest = 0
    for key in month_keys:
        for day in month_days_raw.get(key) or []:
            for evt in getattr(day, "events", None) or []:
                _, text = _format_event(evt, theme)
                if text:
                    longest = max(longest, C.measure(text, event_font))
    month_w = max(_MONTH_MIN_W, min(_MONTH_MAX_W, longest + _MONTH_PAD * 2 + _EVENT_INDENT + SPACE["lg"]))
    event_w = month_w - _MONTH_PAD * 2 - _EVENT_INDENT

    # ---- 逐月算高度，再做「列平衡」排布 ----
    heights: dict[int, int] = {}
    layouts: dict[int, list[list]] = {}
    for key in month_keys:
        month = int(key)
        days = month_days_raw.get(key)
        if not isinstance(days, list):
            continue
        heights[month], layouts[month] = _month_layout(month, days, event_w, theme)

    gap = SPACE["xl"]
    col_x = [0, month_w + gap]
    col_y = [0, 0]
    placements: list[tuple[int, int, int, int]] = []
    for month in sorted(heights):
        column = 0 if col_y[0] <= col_y[1] else 1
        placements.append((month, column, col_y[column], heights[month]))
        col_y[column] += heights[month] + gap
    grid_h = max((column_height - gap for column_height in col_y), default=0)

    season_value = getattr(calendar.season, "value", calendar.season)
    chips = [
        ("当前季节", season_value or "未知"),
        ("年份迭代", f"第{calendar.year_iteration or '未知'}次"),
        ("版本", str(calendar.version) if calendar.version is not None else "未知"),
    ]

    # ---- CodeRabbit R7：画布高度有上限，放不下的月份整月跳过并显式提示 ----
    # 不让超出的月份卡画到画布外（图返回了却看不到内容）。
    from .card_size import DEFAULT_MAX_HEIGHT

    hint_h = FONT["sm"] + SPACE["xs"]
    probe = measure_card_size(
        CardSpec(
            title="1999日历季节信息",
            blocks=[
                ChipsBlock(chips),
                CustomBlock(width=month_w * 2 + gap, height=0),
            ],
            standing="md",
            standing_season=calendar.season,
        )
    )
    grid_budget = DEFAULT_MAX_HEIGHT - probe.height - hint_h
    kept: list[tuple[int, int, int, int]] = []
    dropped: list[int] = []
    col_bottom = [0, 0]
    for month, column, _offset_y, height in placements:
        bottom = col_bottom[column] + height
        if bottom > grid_budget and kept:
            dropped.append(month)
            continue
        kept.append((month, column, col_bottom[column], height))
        col_bottom[column] = bottom + gap
    placements = kept
    grid_h = max((bottom - gap for bottom in col_bottom), default=0)

    size = measure_card_size(
        CardSpec(
            title="1999日历季节信息",
            blocks=[
                ChipsBlock(chips),
                CustomBlock(width=month_w * 2 + gap, height=max(grid_h, 0)),
            ],
            standing="md",
            standing_season=calendar.season,
        )
    )

    page = C.new_page(theme, size.width, size.height)
    y = C.draw_header(page, "1999日历季节信息")
    y = C.draw_chips(page, chips, y) + SPACE["md"]

    grid_w = month_w * 2 + gap
    grid_x = page.content_x + max(0, (page.content_w - grid_w) // 2)
    for month, column, offset_y, height in placements:
        _draw_month(
            page,
            month,
            layouts[month],
            grid_x + col_x[column],
            y + offset_y,
            month_w,
            height,
        )

    bottom_y = y + grid_h
    if dropped:
        names = "、".join(f"{month}月" for month in dropped[:6])
        if len(dropped) > 6:
            names += " 等"
        page.cb.set_color(theme.palette.text_dim).set_font(font("sm"))
        page.cb.add_text(f"… {names}内容较长，未在本图展示", grid_x, bottom_y)
        bottom_y += hint_h

    frame.draw_standing_block(page, bottom_y, "md", season=calendar.season)
    frame.draw_footer_block(page)
    return page.cb.to_image()
