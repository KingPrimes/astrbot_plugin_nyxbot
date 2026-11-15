"""执刑官猎杀卡片渲染器 — 迁移自 Java DefaultDrawLiteSortieImage

版式：页头 + 键值块（Boss / 结束时间）+ 任务表格（任务 / 节点）+ 看板娘 + 署名。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from . import card_frame as frame
from . import components as C
from .card_size import CardSpec, KvBlock, TableBlock, measure_card_size
from .design import SPACE, adapt_color
from .theme import current_theme

if TYPE_CHECKING:
    from PIL import Image

    from ..model.world_state import LiteSortie
    from .card_renderer import CardRenderer


def _format_expiry(lite_sortie: LiteSortie) -> str:
    if lite_sortie.expiry is None:
        return "未知"
    expiry_dt = datetime.fromtimestamp(
        lite_sortie.expiry.time_millis / 1000, tz=timezone.utc
    )
    return expiry_dt.strftime("%Y-%m-%d %H:%M")


def render_lite_sortie_card(
    renderer: CardRenderer,
    lite_sortie: LiteSortie,
) -> Image.Image:
    """绘制执刑官猎杀信息卡片 — 镜像 Java DefaultDrawLiteSortieImage.drawLiteSortieImage()。

    Args:
        renderer: CardRenderer 实例（提供任务类型配色）。
        lite_sortie: LiteSortie 模型。

    Returns:
        PIL Image 对象。
    """
    theme = current_theme()
    palette = theme.palette

    boss_name = lite_sortie.boss.display_name if lite_sortie.boss else "未知"
    info_rows: list[tuple] = [
        ("Boss", boss_name),
        ("结束时间", _format_expiry(lite_sortie)),
    ]

    missions = lite_sortie.missions or []
    columns = [
        C.Column("任务", 1.4, "left", 110),
        C.Column("节点", 2.4, "left", 160),
    ]
    mission_rows: list[list[tuple]] = []
    for mission in missions:
        mission_type = mission.mission_type
        mission_text = mission_type.display_name if mission_type else "未知任务"
        color = (
            adapt_color(renderer.resolve_mission_type_color(mission_type), theme)
            if mission_type
            else palette.text_muted
        )
        mission_rows.append([(mission_text, color), (mission.node or "未知节点", None)])
    if not mission_rows:
        mission_rows = [[("暂无任务信息", palette.text_muted), ("—", palette.text_dim)]]

    size = measure_card_size(
        CardSpec(
            title="执刑官猎杀",
            blocks=[
                KvBlock(info_rows),
                TableBlock(columns=columns, rows=mission_rows),
            ],
            standing="md",
            header_gap=SPACE["md"],
        )
    )

    page = C.new_page(theme, size.width, size.height)
    y = C.draw_header(page, "执刑官猎杀")
    y = C.draw_kv(page, info_rows, y + SPACE["md"])
    y = C.draw_table(page, columns, mission_rows, y + SPACE["md"])
    frame.draw_standing_block(page, y, "md")
    frame.draw_footer_block(page)
    return page.cb.to_image()
