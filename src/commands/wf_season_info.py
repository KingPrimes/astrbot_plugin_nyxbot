"""wf_nightwave - /nightwave or /电波 - 查看午夜电波"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..render.card_renderer import CardRenderer
from ..render.card_season_info import render_season_info_card
from ..service.world_state import WorldStateService


@wf.command("电波")
async def wf_season_info(self, event: AstrMessageEvent):
    """查看午夜电波"""
    nw = await WorldStateService.get_season_info()

    if not nw:
        yield event.plain_result("无法获取午夜电波数据")
        return

    result = await CardRenderer.render_card_to_chain_result(
        render_season_info_card, nw
    )
    yield event.chain_result(result)
