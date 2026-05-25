"""wf_daily_deals - /deals or /每日特惠 - 查看达尔沃每日特惠"""
from __future__ import annotations

import astrbot.api.message_components as Comp
from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..render.card_renderer import CardRenderer
from ..service.world_state import WorldStateService


@wf.command("每日特惠")
async def wf_daily_deals(self, event: AstrMessageEvent):
    """查看达尔沃的每日特惠商品"""
    deals = await WorldStateService.get_daily_deals()

    if not deals:
        yield event.plain_result("当前没有每日特惠数据")
        return

    renderer = CardRenderer()
    from ..render.card_daily_deals import render_daily_deals_card
    img = render_daily_deals_card(renderer, deals)
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
