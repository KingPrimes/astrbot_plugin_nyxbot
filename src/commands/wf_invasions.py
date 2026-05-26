"""wf_invasions - /invasions or /入侵 - 查看当前入侵"""
from __future__ import annotations

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

    result = await CardRenderer.render_card_to_chain_result(
        draw_invasion_card, invasions
    )
    yield event.chain_result(result)
