"""wf_sorties - /sorties or /突击 - 查看今日突击"""
from __future__ import annotations

import astrbot.api.message_components as Comp
from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..render.card_renderer import CardRenderer
from ..render.card_sortie import render_sortie_card
from ..service.world_state import WorldStateService


@wf.command("突击")
async def wf_sorties(self, event: AstrMessageEvent):
    """查看今日突击"""
    sorties = await WorldStateService.get_sorties()

    if not sorties:
        yield event.plain_result("当前没有突击数据")
        return

    sortie_data = sorties[0]

    renderer = CardRenderer()
    img = render_sortie_card(renderer, sortie_data)
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
