"""wf_duviri - /duviri or /双衍 - 查看双衍王境周期"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..render.card_duviri import render_duviri_card
from ..render.card_renderer import CardRenderer
from ..service.world_state import WorldStateService


@wf.command("轮换",alias=["双衍王境"])
async def wf_duviri(self, event: AstrMessageEvent):
    """查看双衍王境周期"""
    duviri = await WorldStateService.get_duviri_cycle()

    if not duviri:
        yield event.plain_result("无法获取双衍王境数据")
        return

    result = await CardRenderer.render_card_to_chain_result(render_duviri_card, duviri)
    yield event.chain_result(result)
