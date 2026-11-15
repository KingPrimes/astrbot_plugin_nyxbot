"""裂隙卡片渲染器

版式：页头（虚空裂隙 / 钢铁裂隙 / 虚空风暴）+ 两列任务卡 + 看板娘 + 署名。

每张卡三行：

1. 档位（``古纪 Lith``，按遗物等级着色）+ 剩余时间（有小时→绿，<10 分→红，其余→黄）；
2. 任务类型（按类型着色）+ 派系图标 + 派系名（按派系着色）；
3. 节点。

卡片宽由三行里最宽的一行决定（夹在 360~560），卡片高由三行行高决定；
画布尺寸交给 :func:`~.card_size.measure_card_size` 累加，不再写死 1200×N。
奇数张时最后一格空着，看板娘填进去并允许向下溢出；偶数张走流式块。
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import card_frame as frame
from . import components as C
from .card_size import CardSpec, CustomBlock, measure_card_size
from .design import FONT, RGB, SPACE, font, semantic_color
from .theme import current_theme

if TYPE_CHECKING:
    from PIL import Image

    from ..model.world_state import ActiveMission
    from .card_renderer import CardRenderer

#: 每行列数。
_COLUMNS = 2
#: 列间距 / 行间距。
_GAP = SPACE["lg"]
#: 卡片内边距。
_CARD_PAD = SPACE["lg"]
#: 卡片宽下限 / 上限（内容再少也不至于挤成竖条，再多也不撑爆画布）。
_MIN_CARD_W = 380
_MAX_CARD_W = 560
#: 卡片高 = 上下内边距 + 三行行高 + 两处行间呼吸（与 ``_draw_card`` 同口径）。
_CARD_H = _CARD_PAD * 2 + FONT["lg"] + SPACE["lg"] + FONT["md"] + SPACE["md"] + FONT["md"]

#: VoidEnum 只有中文名，补齐玩家常用的英文段位名。
_VOID_EN_NAMES: dict[str, str] = {
    "VoidT1": "Lith",
    "VoidT2": "Meso",
    "VoidT3": "Neo",
    "VoidT4": "Axi",
    "VoidT5": "Requiem",
    "VoidT6": "Omnia",
}


@dataclass(frozen=True)
class _FissureRow:
    """一张裂隙卡的全部绘制文案（先算好，绘制与测宽共用）。"""

    tier: str
    tier_color: RGB
    time: str
    time_color: RGB
    mission: str
    mission_color: RGB
    faction: str
    faction_color: RGB
    icon: str
    node: str


def _time_color(text: str, palette) -> RGB:
    """剩余时间配色：含小时→绿；10~59 分→黄；<10 分→红。"""
    lowered = (text or "").lower()
    if "h" in lowered:
        return palette.green
    if "m" in lowered:
        minutes = int(re.sub(r"\D", "", text) or "60")
        return palette.red if minutes < 10 else palette.amber
    return palette.red


def _build_row(mission: ActiveMission, theme) -> _FissureRow:
    """把一条 ``ActiveMission`` 转成绘制用的文案与颜色。"""
    palette = theme.palette

    modifier = mission.modifier
    if modifier is not None:
        suffix = _VOID_EN_NAMES.get(modifier.name, "")
        tier = f"{modifier.display_name} {suffix}".strip()
        tier_color = semantic_color(modifier.color, theme, palette.text_muted)
    else:
        tier, tier_color = "未知等级", palette.text_muted

    time_left = mission.time_left or "未知"
    time_color = _time_color(time_left, palette) if time_left != "未知" else palette.text_muted

    mission_type = mission.mission_type
    if mission_type is not None:
        mission_name = mission_type.display_name
        mission_color = semantic_color(mission_type.color, theme, palette.text_muted)
    else:
        mission_name, mission_color = "未知任务", palette.text_muted

    faction = mission.faction
    icon = getattr(faction, "icon", "") or ""
    if faction is not None and icon:
        faction_name = faction.display_name
        faction_color = semantic_color(faction.color, theme, palette.text_muted)
    else:
        icon = ""
        faction_name = faction.display_name if faction is not None else "未知派系"
        faction_color = palette.text_muted

    return _FissureRow(
        tier=tier,
        tier_color=tier_color,
        time=time_left,
        time_color=time_color,
        mission=mission_name,
        mission_color=mission_color,
        faction=faction_name,
        faction_color=faction_color,
        icon=icon,
        node=mission.node or "未知节点",
    )


def _title_text(fissures: list[ActiveMission]) -> str:
    """标题随数据切换：虚空风暴 > 钢铁裂隙 > 虚空裂隙。"""
    first = fissures[0]
    if first.void_storms:
        return "虚空风暴"
    if first.hard:
        return "钢铁裂隙"
    return "虚空裂隙"


def _row_width(row: _FissureRow, tier_font, body_font) -> int:
    """单张卡最宽的一行（不含内边距）。"""
    line1 = C.measure(row.tier, tier_font) + SPACE["xl"] + C.measure(row.time, body_font)
    line2 = C.measure(row.mission, body_font) + SPACE["md"]
    if row.icon:
        line2 += FONT["md"] + SPACE["sm"]
    line2 += C.measure(row.faction, body_font)
    return max(line1, line2, C.measure(row.node, body_font))


def _draw_card(page, row: _FissureRow, x: int, y: int, width: int) -> None:
    """画一张裂隙卡：底色 + 档位强调条 + 三行信息。"""
    palette = page.palette
    cb = page.cb
    C.draw_grid_card(page, x, y, width, _CARD_H)

    # 顶部强调条（左右内缩，贴合圆角）
    cb.set_color(row.tier_color)
    cb.draw_rounded_rect(x + 14, y + 2, width - 28, 4, radius=2, fill=row.tier_color)

    body_font = font("md")
    inner_w = width - _CARD_PAD * 2

    # 行 1：档位（左）+ 剩余时间（右）
    time_font = font("md")
    time_w = C.measure(row.time, time_font)
    tier_font = font("lg", bold=True)
    cb.set_color(row.tier_color).set_font(tier_font)
    cb.add_text(
        C.fit_text(row.tier, inner_w - time_w - SPACE["md"], tier_font),
        x + _CARD_PAD,
        y + _CARD_PAD,
    )

    cb.set_color(row.time_color).set_font(time_font)
    cb.add_text(
        row.time,
        x + width - _CARD_PAD - time_w,
        y + _CARD_PAD + FONT["lg"] - FONT["md"],
    )

    # 行 2：任务类型 + 派系图标 + 派系名
    cursor = x + _CARD_PAD
    line2_y = y + _CARD_PAD + FONT["lg"] + SPACE["lg"]
    cb.set_color(row.mission_color).set_font(body_font)
    cb.add_text(row.mission, cursor, line2_y)
    cursor += C.measure(row.mission, body_font) + SPACE["md"]

    if row.icon:
        cb.set_color(row.faction_color).set_font(C.icon_font(FONT["md"]))
        cb.add_text(row.icon, cursor, line2_y)
        cursor += FONT["md"] + SPACE["sm"]

    cb.set_color(row.faction_color).set_font(body_font)
    cb.add_text(
        C.fit_text(row.faction, x + width - _CARD_PAD - cursor, body_font),
        cursor,
        line2_y,
    )

    # 行 3：节点
    cb.set_color(palette.text).set_font(body_font)
    cb.add_text(
        C.fit_text(row.node, inner_w, body_font),
        x + _CARD_PAD,
        line2_y + FONT["md"] + SPACE["md"],
    )


def render_fissure_card(
    renderer: CardRenderer,
    fissures: list[ActiveMission],
) -> Image.Image:
    """绘制裂隙信息卡片。

    Args:
        renderer: CardRenderer 实例（保留参数以兼容渲染入口）。
        fissures: ActiveMission 列表（已由 Service 翻译并排序）。

    Returns:
        PIL Image 对象。
    """
    if not fissures:
        return renderer.create_text_image("当前没有活跃的裂隙", 800, 120)

    theme = current_theme()
    rows = [_build_row(mission, theme) for mission in fissures]
    title = _title_text(fissures)
    subtitle = f"共 {len(rows)} 个任务"

    # ---- 卡片宽：三行里最宽的一行，夹在 [380, 560] ----
    tier_font = font("lg", bold=True)
    body_font = font("md")
    intrinsic = max(_row_width(row, tier_font, body_font) for row in rows)
    card_w = max(_MIN_CARD_W, min(_MAX_CARD_W, intrinsic + _CARD_PAD * 2))

    count = len(rows)
    grid_rows = math.ceil(count / _COLUMNS)
    grid_w = card_w * _COLUMNS + _GAP
    grid_h = grid_rows * _CARD_H + (grid_rows - 1) * _GAP

    # ---- 奇数张：最后一格空着 → 看板娘填进去，允许向下溢出 ----
    empty_slot = count % _COLUMNS != 0
    slot_w = card_w - _CARD_PAD * 2
    slot = frame.standing_cell_size(slot_w, _CARD_H * 2) if empty_slot else (0, 0)
    if slot[1]:
        extra_h = max(0, slot[1] - _CARD_H)
        standing = None
    else:
        extra_h = 0
        standing = "md"

    size = measure_card_size(
        CardSpec(
            title=title,
            subtitle=subtitle,
            blocks=[CustomBlock(width=grid_w, height=grid_h + extra_h)],
            standing=standing,
        )
    )

    page = C.new_page(theme, size.width, size.height)
    y = C.draw_header(page, title, subtitle)

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


# 兼容旧名：命令层与第三方调用仍可用 draw_fissure_card
draw_fissure_card = render_fissure_card
