"""wf_calendar_seasons - 1999日历季节指令

指令:
  /1999  or  /日历  → 查看1999日历季节信息
"""
from __future__ import annotations

import astrbot.api.message_components as Comp
from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..render.card_calendar_seasons import render_calendar_seasons_card
from ..render.card_renderer import CardRenderer
from ..service.world_state import WorldStateService


@wf.command(name="1999",alias=["日历"])
async def wf_calendar_1999(self, event: AstrMessageEvent):
    """查看1999日历季节信息"""
    calendars = await WorldStateService.get_known_calendar_seasons()

    if not calendars:
        yield event.plain_result("当前没有1999日历数据")
        return

    renderer = CardRenderer()
    img = render_calendar_seasons_card(renderer, calendars)
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
