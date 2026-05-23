"""wf_duviri - /duviri or /双衍 - 查看双衍王境周期"""
from __future__ import annotations

import astrbot.api.message_components as Comp
from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..render.card_renderer import CardRenderer
from ..service.world_state import WorldStateService


@wf.command("双衍")
async def wf_duviri(self, event: AstrMessageEvent):
    """查看双衍王境周期"""
    duviri = await WorldStateService.get_duviri_cycle()

    if not duviri:
        yield event.plain_result("无法获取双衍王境数据")
        return

    duviri_data = {
        "state": duviri.state,
        "is_day": None,  # 双衍王境不是日夜循环
        "time_left": duviri.time_left,
        "spiral": duviri.state,
        "commander": "",
    }

    renderer = CardRenderer()
    img = renderer.create_duviri_card(duviri_data)
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
