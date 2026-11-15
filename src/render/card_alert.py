"""警报卡片渲染器

版式：页头（``警报``）+ 两列警报卡 + 看板娘 + 署名。

每张卡三行：

1. 节点（粗体）+ 剩余时间（琥珀色，右对齐）；
2. 任务类型 + 派系图标 + 派系名（各按自身颜色）；
3. 奖励（金色，星币 + 最多 5 件物品，超宽截断）。

卡片宽 = 三行里最宽的一行（夹在 400~560），高 = 三行行高之和（120）。
奇数条时最后一格空着，看板娘填进去；偶数条走流式块。
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import card_frame as frame
from . import components as C
from .card_size import CardSpec, CustomBlock, measure_card_size
from .design import FONT, RGB, SPACE, font, semantic_color
from .theme import current_theme

if TYPE_CHECKING:
    from PIL import Image

    from ..model.world_state import Alert
    from .card_renderer import CardRenderer

#: 每行列数。
_COLUMNS = 2
#: 列间距 / 行间距。
_GAP = SPACE["lg"]
#: 卡片内边距。
_CARD_PAD = SPACE["lg"]
#: 卡片宽下限 / 上限。
_MIN_CARD_W = 400
_MAX_CARD_W = 560
#: 卡片高 = 上下内边距 + 三行行高 + 两处行间呼吸（与 ``_draw_card`` 同口径）。
_CARD_H = _CARD_PAD * 2 + FONT["md"] + SPACE["md"] + FONT["md"] + SPACE["sm"] + FONT["base"]


@dataclass(frozen=True)
class _AlertRow:
    """一条警报的绘制文案。"""

    node: str
    eta: str
    mission: str
    mission_color: RGB
    faction: str
    faction_color: RGB
    icon: str
    reward: str


def _reward_text(alert: Alert) -> str:
    """奖励单行文本：星币 + 最多 5 件物品（数量 > 1 时带 ×N）。"""
    info = alert.mission_info
    reward = info.mission_reward if info is not None else None
    if reward is None:
        return ""

    segments: list[str] = []
    if reward.credits and reward.credits > 0:
        segments.append(f"{reward.credits} 星币")
    if reward.counted_items:
        items = [
            f"{item.name}×{item.count}" if item.count > 1 else item.name
            for item in reward.counted_items[:5]
        ]
        segments.append("  ".join(items))
    return "   ".join(segment for segment in segments if segment)


def _build_row(alert: Alert, theme) -> _AlertRow:
    """把一条 ``Alert`` 转成绘制文案。"""
    palette = theme.palette
    info = alert.mission_info

    node = (info.location if info and info.location else "") or "未知节点"

    mission_type = info.mission_type if info is not None else None
    if mission_type is not None:
        mission = mission_type.display_name
        mission_color = semantic_color(mission_type.color, theme, palette.text_muted)
    else:
        mission, mission_color = "未知任务", palette.text_muted

    faction = info.faction if info is not None else None
    icon = getattr(faction, "icon", "") or ""
    if faction is not None and icon:
        faction_name = faction.display_name
        faction_color = semantic_color(faction.color, theme, palette.text_muted)
    else:
        icon = ""
        faction_name = faction.display_name if faction is not None else "未知派系"
        faction_color = palette.text_muted

    return _AlertRow(
        node=node,
        eta=alert.time_left or "未知",
        mission=mission,
        mission_color=mission_color,
        faction=faction_name,
        faction_color=faction_color,
        icon=icon,
        reward=_reward_text(alert),
    )


def _row_width(row: _AlertRow, body_font, small_font) -> int:
    """单张卡最宽的一行（不含内边距）。"""
    line1 = C.measure(row.node, font("md", bold=True)) + SPACE["xl"] + C.measure(row.eta, body_font)
    line2 = C.measure(row.mission, body_font) + SPACE["md"]
    if row.icon:
        line2 += FONT["md"] + SPACE["sm"]
    line2 += C.measure(row.faction, body_font)
    line3 = C.measure(row.reward, small_font)
    return max(line1, line2, line3)


def _draw_card(page, row: _AlertRow, x: int, y: int, width: int) -> None:
    """画一张警报卡。"""
    palette = page.palette
    cb = page.cb
    C.draw_grid_card(page, x, y, width, _CARD_H)

    body_font = font("md")
    small_font = font("base")
    inner_w = width - _CARD_PAD * 2

    # 行 1：节点（左）+ 剩余时间（右）
    eta_w = C.measure(row.eta, body_font)
    node_font = font("md", bold=True)
    cb.set_color(palette.text).set_font(node_font)
    cb.add_text(
        C.fit_text(row.node, inner_w - eta_w - SPACE["lg"], node_font),
        x + _CARD_PAD,
        y + _CARD_PAD,
    )
    cb.set_color(palette.amber).set_font(body_font)
    cb.add_text(row.eta, x + width - _CARD_PAD - eta_w, y + _CARD_PAD)

    # 行 2：任务类型 + 派系图标 + 派系名
    line2_y = y + _CARD_PAD + FONT["md"] + SPACE["md"]
    cursor = x + _CARD_PAD
    cb.set_color(row.mission_color).set_font(body_font)
    cb.add_text(row.mission, cursor, line2_y)
    cursor += C.measure(row.mission, body_font) + SPACE["md"]

    if row.icon:
        cb.set_color(row.faction_color).set_font(C.icon_font(FONT["md"]))
        cb.add_text(row.icon, cursor, line2_y)
        cursor += FONT["md"] + SPACE["sm"]

    cb.set_color(row.faction_color).set_font(body_font)
    cb.add_text(C.fit_text(row.faction, x + width - _CARD_PAD - cursor, body_font), cursor, line2_y)

    # 行 3：奖励
    if row.reward:
        cb.set_color(palette.gold).set_font(small_font)
        cb.add_text(
            C.fit_text(row.reward, inner_w, small_font),
            x + _CARD_PAD,
            line2_y + FONT["md"] + SPACE["sm"],
        )


def render_alert_card(renderer: CardRenderer, alerts: list[Alert]) -> Image.Image:
    """绘制警报信息卡片。

    Args:
        renderer: CardRenderer 实例（保留参数以兼容渲染入口）。
        alerts: Alert 模型列表。

    Returns:
        PIL Image 对象。
    """
    if not alerts:
        return renderer.create_text_image("当前没有活跃的警报", 800, 120)

    theme = current_theme()
    rows = [_build_row(alert, theme) for alert in alerts]
    subtitle = f"共 {len(rows)} 条警报"

    # ---- 卡片宽：三行里最宽的一行，夹在 [400, 560] ----
    body_font = font("md")
    small_font = font("base")
    intrinsic = max(_row_width(row, body_font, small_font) for row in rows)
    card_w = max(_MIN_CARD_W, min(_MAX_CARD_W, intrinsic + _CARD_PAD * 2))

    count = len(rows)
    grid_rows = math.ceil(count / _COLUMNS)
    grid_w = card_w * _COLUMNS + _GAP
    grid_h = grid_rows * _CARD_H + (grid_rows - 1) * _GAP

    # ---- 奇数条：最后一格空着 → 看板娘填进去，允许向下溢出 ----
    empty_slot = count % _COLUMNS != 0
    slot_w = card_w - _CARD_PAD * 2
    slot = frame.standing_cell_size(slot_w, _CARD_H * 2) if empty_slot else (0, 0)
    extra_h = max(0, slot[1] - _CARD_H) if slot[1] else 0
    standing = None if slot[1] else "md"

    size = measure_card_size(
        CardSpec(
            title="警报",
            subtitle=subtitle,
            blocks=[CustomBlock(width=grid_w, height=grid_h + extra_h)],
            standing=standing,
        )
    )

    page = C.new_page(theme, size.width, size.height)
    y = C.draw_header(page, "警报", subtitle)

    grid_x = page.content_x + max(0, (page.content_w - grid_w) // 2)
    for index, row in enumerate(rows):
        row_index, column = divmod(index, _COLUMNS)
        _draw_card(
            page,
            row,
            grid_x + column * (card_w + _GAP),
            y + row_index * (_CARD_H + _GAP),
            card_w,
        )

    if slot[1]:
        slot_y = y + (grid_rows - 1) * (_CARD_H + _GAP)
        frame.draw_standing_in_cell(
            page,
            grid_x + (count % _COLUMNS) * (card_w + _GAP) + _CARD_PAD,
            slot_y,
            slot_w,
            _CARD_H * 2,
        )
    else:
        frame.draw_standing_block(page, y + grid_h, "md")

    frame.draw_footer_block(page)
    return page.cb.to_image()
