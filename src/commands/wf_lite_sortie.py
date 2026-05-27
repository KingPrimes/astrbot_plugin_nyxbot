"""wf_lite_sortie - /执刑官猎杀 - 查看执刑官猎杀任务"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..config.config import get_qq_markdown_enabled
from ..markdown.lite_sortie import format_lite_sorties_markdown
from ..render.card_lite_sortie import render_lite_sortie_card
from ..render.card_renderer import CardRenderer
from ..service.world_state import WorldStateService
from ..util.markdown_utils import is_qq_official


@wf.command("执刑官猎杀", alias=["猎杀", "执行官", "执政官", "执刑官"])
async def wf_lite_sortie(self, event: AstrMessageEvent):
    """查看本周执刑官猎杀（Archon Hunt）"""
    lite_sorties = await WorldStateService.get_lite_sortie()

    if not lite_sorties:
        yield event.plain_result("当前没有执刑官猎杀数据")
        return

    lite_sortie_data = lite_sorties[0]

    if is_qq_official(event) and get_qq_markdown_enabled():
        yield event.plain_result(format_lite_sorties_markdown(lite_sortie_data))
    else:
        result = await CardRenderer.render_card_to_chain_result(
            render_lite_sortie_card, lite_sortie_data
        )
        yield event.chain_result(result)
