"""突击卡片渲染器 — 迁移自 Java DefaultDrawSortiesImage

版式：页头（副标题显示 Boss）+ 变体表格（任务 / 节点 / 修饰符）+ 看板娘 + 署名。
任务类型颜色走 ``CardRenderer.resolve_mission_type_color``，再经 ``adapt_color``
按当前主题校正对比度。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from . import card_frame as frame
from . import components as C
from .card_size import CardSpec, TableBlock, measure_card_size
from .design import adapt_color
from .theme import current_theme

if TYPE_CHECKING:
    from PIL import Image

    from ..model.world_state import Sortie
    from .card_renderer import CardRenderer


def render_sortie_card(renderer: CardRenderer, sortie: Sortie) -> Image.Image:
    """绘制突击信息卡片 — 镜像 Java DefaultDrawSortiesImage.drawSortiesImage()。

    Args:
        renderer: CardRenderer 实例（提供任务类型配色）。
        sortie: Sortie 模型。

    Returns:
        PIL Image 对象。
    """
    theme = current_theme()
    palette = theme.palette

    variants = sortie.variants or []
    boss_name = sortie.boss.display_name if sortie.boss else "未知"
    subtitle = f"Boss: {boss_name}"

    columns = [
        C.Column("任务", 1.5, "left", 110),
        C.Column("节点", 2.3, "left", 160),
        C.Column("修饰符", 1.7, "left", 140),
    ]
    rows: list[list[tuple]] = []
    for variant in variants:
        mission_type = variant.mission_type
        mission_text = mission_type.display_name if mission_type else "未知任务"
        color = (
            adapt_color(renderer.resolve_mission_type_color(mission_type), theme)
            if mission_type
            else palette.text_muted
        )
        node = variant.node or "未知节点"
        modifier = variant.modifier_type or "无"
        rows.append(
            [
                (mission_text, color),
                (node, None),
                (modifier, palette.amber),
            ]
        )

    if not rows:
        rows = [[("暂无任务数据", palette.text_muted), ("—", palette.text_dim), ("—", palette.text_dim)]]

    size = measure_card_size(
        CardSpec(
            title="突击任务",
            subtitle=subtitle,
            blocks=[TableBlock(columns=columns, rows=rows)],
            standing="md",
        )
    )

    page = C.new_page(theme, size.width, size.height)
    y = C.draw_header(page, "突击任务", subtitle)
    y = C.draw_table(page, columns, rows, y)
    frame.draw_standing_block(page, y, "md")
    frame.draw_footer_block(page)
    return page.cb.to_image()
