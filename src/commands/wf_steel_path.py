"""wf_steel_path - /steel or /钢铁 - 查看钢铁之路"""
from __future__ import annotations

import astrbot.api.message_components as Comp
from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..service.world_state import WorldStateService


@wf.command("钢铁")
async def wf_steel_path(self, event: AstrMessageEvent):
    """查看钢铁之路"""
    from ..render.card_renderer import CardRenderer
    from ..render.card_steel_path import render_steel_path_card

    sp = await WorldStateService.get_steel_path()

    if not sp:
        yield event.plain_result("无法获取钢铁之路数据")
        return

    img = render_steel_path_card(None, sp)
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
