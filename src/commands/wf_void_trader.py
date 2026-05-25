"""wf_void_trader - /void or /奸商 - 查看虚空商人"""
from __future__ import annotations

import astrbot.api.message_components as Comp
from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..render.card_renderer import CardRenderer
from ..service.world_state import WorldStateService


@wf.command("奸商",alias=["虚空商人"])
async def wf_void_trader(self, event: AstrMessageEvent):
    """查看虚空商人（Baro Ki'Teer）"""
    vt = await WorldStateService.get_void_trader()

    if not vt:
        yield event.plain_result("虚空商人未找到数据")
        return

    renderer = CardRenderer()
    img = renderer.create_void_trader_card(vt)
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
