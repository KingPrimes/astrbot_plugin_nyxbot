"""wf_invasions - /invasions or /入侵 - 查看当前入侵"""
from __future__ import annotations

import astrbot.api.message_components as Comp
from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..render.card_renderer import CardRenderer
from ..service.world_state import WorldStateService


@wf.command("入侵")
async def wf_invasions(self, event: AstrMessageEvent):
    """查看当前入侵"""
    invasions = await WorldStateService.get_invasions()

    if not invasions:
        yield event.plain_result("当前没有活跃的入侵")
        return

    renderer = CardRenderer()
    from ..render.card_invasions import draw_invasion_card
    img = draw_invasion_card(renderer, invasions)
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
