"""wf_cycle - /cycle or /平原 - 查看平原周期时间"""
from __future__ import annotations

import astrbot.api.message_components as Comp
from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..model.world_state.all_cycles import AllCycles
from ..render.card_cycle import render_cycle_card
from ..render.card_renderer import CardRenderer
from ..service.world_state import WorldStateService


@wf.command("平原")
async def wf_cycle(self, event: AstrMessageEvent):
    """查看所有平原周期（地球、希图斯、金星、扎里曼、魔胎之境）"""

    # 并发获取所有周期数据 / Fetch all cycle data concurrently
    earth = await WorldStateService.get_earth_cycle()
    cetus = await WorldStateService.get_cetus_cycle()
    vallis = await WorldStateService.get_vallis_cycle()
    zariman = await WorldStateService.get_zariman_cycle()
    cambion = await WorldStateService.get_cambion_cycle()

    if not any((earth, cetus, vallis, zariman, cambion)):
        yield event.plain_result("无法获取周期数据")
        return

    # 构建 AllCycles 对象 / Build AllCycles instance
    all_cycles = AllCycles()
    all_cycles.earth = earth
    all_cycles.cetus = cetus
    all_cycles.vallis = vallis
    all_cycles.zariman = zariman
    all_cycles.cambion = cambion

    renderer = CardRenderer()
    img = render_cycle_card(renderer, all_cycles, "全周期状态")
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
