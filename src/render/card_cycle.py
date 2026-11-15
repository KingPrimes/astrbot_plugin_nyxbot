"""周期卡片渲染器

对应 Java DefaultDrawAllCycleImage.java。
版式：页头 + 表格（地点 / 状态 / 剩余）+ 看板娘 + 署名；
状态图标走 icon_registry（sun / night / cold），颜色随「暖/冷」状态。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from . import card_frame as frame
from . import components as C
from .card_size import CardSpec, TableBlock, measure_card_size
from .icon_registry import icon_char
from .theme import current_theme

if TYPE_CHECKING:
    from PIL import Image

    from ..model.world_state.all_cycles import AllCycles
    from .card_renderer import CardRenderer


class _CycleRow:
    """单行周期渲染数据 / Single cycle row rendering data."""

    __slots__ = ("name", "icon_token", "is_warm", "state_text", "time_left")

    def __init__(
        self,
        name: str,
        icon_token: str,
        is_warm: bool,
        state_text: str,
        time_left: str,
    ) -> None:
        self.name = name
        self.icon_token = icon_token
        self.is_warm = is_warm
        self.state_text = state_text
        self.time_left = time_left


def _build_rows(cycles: AllCycles) -> list[_CycleRow]:
    """从 AllCycles 构建渲染行列表 / Build row list from AllCycles data.

    逻辑对应 Java DefaultDrawAllCycleImage:
    - Earth/Cetus: is_day → warm+SUN, else cold+NIGHT
    - Vallis: is_warm → warm+SUN, else cold+COLD
    - Cambion: active=="FASS" → warm+SUN, else cold+NIGHT
    - Zariman: is_corpus → warm+GRINEER, else cold+CORPUS
    """
    rows: list[_CycleRow] = []

    if cycles.earth:
        rows.append(
            _CycleRow(
                "地球",
                "sun" if cycles.earth.is_day else "night",
                cycles.earth.is_day,
                cycles.earth.state,
                cycles.earth.time_left,
            )
        )

    if cycles.cetus:
        rows.append(
            _CycleRow(
                "希图斯（夜灵平野）",
                "sun" if cycles.cetus.is_day else "night",
                cycles.cetus.is_day,
                cycles.cetus.state,
                cycles.cetus.time_left,
            )
        )

    if cycles.vallis:
        rows.append(
            _CycleRow(
                "福尔图娜（奥布山谷）",
                "sun" if cycles.vallis.is_warm else "cold",
                cycles.vallis.is_warm,
                cycles.vallis.state,
                cycles.vallis.time_left,
            )
        )

    if cycles.cambion:
        is_fass = cycles.cambion.active == "FASS"
        rows.append(
            _CycleRow(
                "魔胎之境（火卫二）",
                "sun" if is_fass else "night",
                is_fass,
                cycles.cambion.active,
                cycles.cambion.time_left,
            )
        )

    if cycles.zariman:
        # 扎里曼用派系图标表达「科体/科普斯」，注册表里对应 grineer / corpus
        rows.append(
            _CycleRow(
                "扎里曼号",
                "grineer" if cycles.zariman.is_corpus else "corpus",
                cycles.zariman.is_corpus,
                cycles.zariman.state,
                cycles.zariman.time_left,
            )
        )

    return rows


def render_cycle_card(
    renderer: CardRenderer,
    cycles: AllCycles,
    title: str = "平原周期",
) -> Image.Image:
    """绘制周期信息卡片。

    Args:
        renderer: CardRenderer 实例（保留参数以兼容渲染入口）。
        cycles: AllCycles 聚合对象。
        title: 卡片标题。
    """
    rows = _build_rows(cycles)
    if not rows:
        return renderer.create_text_image("无周期数据")

    theme = current_theme()
    palette = theme.palette

    columns = [
        C.Column("地点", 2.4, "left", 160),
        C.Column("状态", 1.2, "left", 90),
        C.Column("剩余", 1.2, "right", 100),
    ]
    table_rows: list[list[tuple]] = []
    for row in rows:
        color = palette.gold if row.is_warm else palette.blue
        table_rows.append(
            [
                (row.name, None),
                (row.state_text, color, icon_char(row.icon_token), color),
                (row.time_left or "—", palette.text_muted),
            ]
        )

    size = measure_card_size(
        CardSpec(
            title=title,
            blocks=[TableBlock(columns=columns, rows=table_rows)],
            standing="sm",
        )
    )

    page = C.new_page(theme, size.width, size.height)
    y = C.draw_header(page, title)
    y = C.draw_table(page, columns, table_rows, y)
    frame.draw_standing_block(page, y, "sm")
    frame.draw_footer_block(page)
    return page.cb.to_image()
