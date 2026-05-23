"""wf_nightwave - /nightwave or /电波 - 查看午夜电波"""
from __future__ import annotations

import astrbot.api.message_components as Comp
from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..render.card_renderer import CardRenderer
from ..service.world_state import WorldStateService


@wf.command("电波")
async def wf_nightwave(self, event: AstrMessageEvent):
    """查看午夜电波"""
    nw = await WorldStateService.get_nightwave()

    if not nw:
        yield event.plain_result("无法获取午夜电波数据")
        return

    renderer = CardRenderer()
    img = renderer.create_nightwave_card(nw)
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
