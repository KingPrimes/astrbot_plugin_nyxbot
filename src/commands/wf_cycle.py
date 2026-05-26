"""wf_cycle - /cycle or /平原 - 查看平原周期时间"""
from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..model.world_state.all_cycles import AllCycles
from ..render.card_cycle import render_cycle_card
from ..render.card_renderer import CardRenderer
from ..service.world_state import WorldStateService


def _safe(results: Sequence[object]) -> list[Any]:
    """将 gather(return_exceptions=True) 中的异常统一替换为 None。"""
    return [None if isinstance(r, BaseException) else r for r in results]


@wf.command("平原")
async def wf_cycle(self, event: AstrMessageEvent):
    """查看所有平原周期（地球、希图斯、金星、扎里曼、魔胎之境）"""

    # 并发获取所有周期数据 / Fetch all cycle data concurrently
    earth, cetus, vallis, zariman, cambion = _safe(await asyncio.gather(
        WorldStateService.get_earth_cycle(),
        WorldStateService.get_cetus_cycle(),
        WorldStateService.get_vallis_cycle(),
        WorldStateService.get_zariman_cycle(),
        WorldStateService.get_cambion_cycle(),
        return_exceptions=True,
    ))

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
