"""wf_lite_sortie - /执刑官猎杀 - 查看执刑官猎杀任务"""
from __future__ import annotations

import astrbot.api.message_components as Comp
from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..render.card_lite_sortie import render_lite_sortie_card
from ..render.card_renderer import CardRenderer
from ..service.world_state import WorldStateService


@wf.command("执刑官猎杀",alias=["猎杀","执行官","执政官","执刑官"])
async def wf_lite_sortie(self, event: AstrMessageEvent):
    """查看本周执刑官猎杀（Archon Hunt）"""
    lite_sorties = await WorldStateService.get_lite_sortie()

    if not lite_sorties:
        yield event.plain_result("当前没有执刑官猎杀数据")
        return

    lite_sortie_data = lite_sorties[0]

    renderer = CardRenderer()
    img = render_lite_sortie_card(renderer, lite_sortie_data)
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
