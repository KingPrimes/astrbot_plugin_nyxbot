"""wf_nightwave - /nightwave or /电波 - 查看午夜电波"""
from __future__ import annotations

import astrbot.api.message_components as Comp
from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..render.card_renderer import CardRenderer
from ..service.world_state import WorldStateService


@wf.command("电波")
async def wf_season_info(self, event: AstrMessageEvent):
    """查看午夜电波"""
    nw = await WorldStateService.get_season_info()

    if not nw:
        yield event.plain_result("无法获取午夜电波数据")
        return

    from ..render.card_season_info import render_season_info_card

    renderer = CardRenderer()
    img = render_season_info_card(renderer, nw)
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
