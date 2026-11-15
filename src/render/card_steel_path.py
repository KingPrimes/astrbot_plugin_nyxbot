"""钢铁之路卡片渲染器 — 迁移自 Java DefaultDrawSteelPathImage

版式（design + components）：
  - 页头「钢铁奖励」+ 分割线
  - 键值块：当前奖励 / 下一个奖励 / 剩余时间
  - 内容下方看板娘（md）+ 页脚署名（读品牌设置）
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from . import card_frame as frame
from . import components as C
from .card_size import CardSpec, KvBlock, measure_card_size
from .design import SPACE
from .theme import current_theme

if TYPE_CHECKING:
    from PIL import Image

    from ..model.world_state import SteelPathOffering
    from .card_renderer import CardRenderer


def render_steel_path_card(
    renderer: CardRenderer,
    steel_path: SteelPathOffering,
) -> Image.Image:
    """绘制钢铁之路信息卡片 — 镜像 Java DefaultDrawSteelPathImage.drawSteelPathImage()。

    Args:
        renderer: CardRenderer 实例（保留参数以兼容渲染入口）。
        steel_path: SteelPathOffering 模型。

    Returns:
        PIL Image 对象。
    """
    theme = current_theme()
    palette = theme.palette

    rows: list[tuple] = []
    if steel_path.current_reward:
        rows.append(("当前奖励", steel_path.current_reward.name))
    if steel_path.next_reward:
        rows.append(("下一个奖励", steel_path.next_reward.name))
    rows.append(("剩余时间", steel_path.remaining or "未知", palette.amber))

    size = measure_card_size(
        CardSpec(
            title="钢铁奖励",
            blocks=[KvBlock(rows)],
            standing="md",
            header_gap=SPACE["md"],
        )
    )

    page = C.new_page(theme, size.width, size.height)
    y = C.draw_header(page, "钢铁奖励")
    y = C.draw_kv(page, rows, y + SPACE["md"])
    frame.draw_standing_block(page, y, "md")
    frame.draw_footer_block(page)
    return page.cb.to_image()
