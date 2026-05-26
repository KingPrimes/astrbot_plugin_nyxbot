"""wf_fissures - 裂隙指令

指令:
  /裂隙       → 普通虚空裂隙
  /钢铁裂隙   → 钢铁之路裂隙
  /九重天裂隙 → 虚空风暴 (Railjack)
"""
from __future__ import annotations

import astrbot.api.message_components as Comp
from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..render.card_fissures import draw_fissure_card
from ..render.card_renderer import CardRenderer
from ..service.world_state import WorldStateService
from ..wenum.fissure_type import FissureTypeEnum


async def _render_fissures(event: AstrMessageEvent, fissure_type: FissureTypeEnum, label: str):
    """通用：获取并渲染指定类型的裂隙卡片。"""
    fissures = await WorldStateService.get_fissures(fissure_type)

    if not fissures:
        yield event.plain_result(f"当前没有活跃的{label}")
        return

    renderer = CardRenderer()
    img = draw_fissure_card(renderer, fissures)
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])


@wf.command("裂隙",alias=["裂缝"])
async def wf_fissures(self, event: AstrMessageEvent):
    """查看普通虚空裂隙"""
    async for result in _render_fissures(event, FissureTypeEnum.ACTIVE_MISSION, "裂隙"):
        yield result


@wf.command("钢铁裂隙",alias=["钢铁裂缝"])
async def wf_fissures_steel_path(self, event: AstrMessageEvent):
    """查看钢铁之路裂隙"""
    async for result in _render_fissures(event, FissureTypeEnum.STEEL_PATH, "钢铁裂隙"):
        yield result


@wf.command("九重天裂隙",alias=["九重天","九重天裂缝"])
async def wf_fissures_void_storms(self, event: AstrMessageEvent):
    """查看虚空风暴（九重天裂隙）"""
    async for result in _render_fissures(event, FissureTypeEnum.VOID_STORMS, "虚空风暴"):
        yield result
