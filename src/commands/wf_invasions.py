"""wf_invasions - /invasions or /入侵 - 查看当前入侵"""
from __future__ import annotations

import asyncio

import astrbot.api.message_components as Comp
from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..render.card_invasions import draw_invasion_card
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
    loop = asyncio.get_running_loop()
    img_bytes = await loop.run_in_executor(
        None,
        lambda: CardRenderer.render_to_bytes(draw_invasion_card(renderer, invasions)),
    )
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
