"""wf_cycle - /cycle or /平原 - 查看平原周期时间"""
from __future__ import annotations

import asyncio
from typing import cast

from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..model.world_state.all_cycles import AllCycles
from ..model.world_state.cambion_cycle import CambionCycle
from ..model.world_state.cetus_cycle import CetusCycle
from ..model.world_state.earth_cycle import EarthCycle
from ..model.world_state.vallis_cycle import VallisCycle
from ..model.world_state.zariman_cycle import ZarimanCycle
from ..render.card_cycle import render_cycle_card
from ..render.card_renderer import CardRenderer
from ..service.world_state import WorldStateService


@wf.command("平原")
async def wf_cycle(self, event: AstrMessageEvent):
    """查看所有平原周期（地球、希图斯、金星、扎里曼、魔胎之境）"""

    # 并发获取所有周期数据 / Fetch all cycle data concurrently
    results = await asyncio.gather(
        WorldStateService.get_earth_cycle(),
        WorldStateService.get_cetus_cycle(),
        WorldStateService.get_vallis_cycle(),
        WorldStateService.get_zariman_cycle(),
        WorldStateService.get_cambion_cycle(),
        return_exceptions=True,
    )

    earth = cast(EarthCycle | None, results[0] if not isinstance(results[0], BaseException) else None)
    cetus = cast(CetusCycle | None, results[1] if not isinstance(results[1], BaseException) else None)
    vallis = cast(VallisCycle | None, results[2] if not isinstance(results[2], BaseException) else None)
    zariman = cast(ZarimanCycle | None, results[3] if not isinstance(results[3], BaseException) else None)
    cambion = cast(CambionCycle | None, results[4] if not isinstance(results[4], BaseException) else None)

    if not any((earth, cetus, vallis, zariman, cambion)):
        yield event.plain_result("无法获取周期数据")
        return

    # 构建 AllCycles 对象 / Build AllCycles instance
    all_cycles = AllCycles(
        earth=earth,
        cetus=cetus,
        vallis=vallis,
        zariman=zariman,
        cambion=cambion,
    )

    result = await CardRenderer.render_card_to_chain_result(
        render_cycle_card, all_cycles, "全周期状态"
    )
    yield event.chain_result(result)
