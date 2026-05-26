"""wf_void_trader - /void or /奸商 - 查看虚空商人"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..render.card_renderer import CardRenderer
from ..render.card_void_trader import render_void_trader_card
from ..service.world_state import WorldStateService


@wf.command("奸商",alias=["虚空商人"])
async def wf_void_trader(self, event: AstrMessageEvent):
    """查看虚空商人（Baro Ki'Teer）"""


    vt = await WorldStateService.get_void_trader()

    if not vt:
        yield event.plain_result("虚空商人未找到数据")
        return

    result = await CardRenderer.render_card_to_chain_result(
        render_void_trader_card, vt
    )
    yield event.chain_result(result)
