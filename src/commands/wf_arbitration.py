"""wf_arbitration - /arbitration or /仲裁 - 查看当前仲裁

镜像 Java: ArbitrationPlugin.java
"""
from __future__ import annotations

import astrbot.api.message_components as Comp
from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..render.card_arbitration import render_arbitration_card
from ..render.card_renderer import CardRenderer
from ..service.world_state import WorldStateService


@wf.command("仲裁")
async def wf_arbitration(self, event: AstrMessageEvent):
    """查看当前仲裁任务。"""
    arbitration = await WorldStateService.get_arbitration()

    if arbitration is None:
        yield event.plain_result("当前没有活跃的仲裁任务")
        return

    renderer = CardRenderer()
    img = render_arbitration_card(renderer, arbitration)
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
