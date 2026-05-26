"""wf_steel_path - /steel or /钢铁 - 查看钢铁之路"""
from __future__ import annotations

import asyncio

import astrbot.api.message_components as Comp
from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..render.card_renderer import CardRenderer
from ..render.card_steel_path import render_steel_path_card
from ..service.world_state import WorldStateService


@wf.command("钢铁")
async def wf_steel_path(self, event: AstrMessageEvent):
    """查看钢铁之路"""


    sp = await WorldStateService.get_steel_path()

    if not sp:
        yield event.plain_result("无法获取钢铁之路数据")
        return

    loop = asyncio.get_running_loop()
    img_bytes = await loop.run_in_executor(
        None,
        lambda: CardRenderer.render_to_bytes(render_steel_path_card(sp)),
    )
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
