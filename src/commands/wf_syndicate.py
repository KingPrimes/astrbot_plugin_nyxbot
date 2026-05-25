"""wf_syndicate - 集团赏金任务指令

指令:
  /希图斯 or /地球赏金  → 希图斯 (Ostron) 赏金
  /英择谛 or /火卫二赏金 → 英择谛 (Entrati) 赏金
  /索拉里斯 or /金星赏金  → 索拉里斯联盟 (Solaris United) 赏金
"""
from __future__ import annotations

import astrbot.api.message_components as Comp
from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..render.card_renderer import CardRenderer
from ..service.world_state import WorldStateService
from ..wenum.world_state.syndicate import SyndicateEnum


async def _render_syndicate(event: AstrMessageEvent, syndicate: SyndicateEnum, name: str):
    """通用：获取并渲染指定集团的赏金任务卡片。"""
    sm = await WorldStateService.get_syndicate_mission(syndicate)

    if sm is None:
        yield event.plain_result(f"当前没有{name}赏金数据")
        return

    renderer = CardRenderer()
    img = renderer.create_syndicate_card(sm)
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])


@wf.command("希图斯",alias=["地球赏金"])
async def wf_syndicate_cetus(self, event: AstrMessageEvent):
    """希图斯（Ostron）赏金任务"""
    async for result in _render_syndicate(event, SyndicateEnum.CetusSyndicate, "希图斯"):
        yield result


@wf.command("英择谛",alias=["火卫二赏金"])
async def wf_syndicate_entrati(self, event: AstrMessageEvent):
    """英择谛（Entrati）赏金任务"""
    async for result in _render_syndicate(event, SyndicateEnum.EntratiSyndicate, "英择谛"):
        yield result


@wf.command("索拉里斯",alias=["金星赏金"])
async def wf_syndicate_solaris(self, event: AstrMessageEvent):
    """索拉里斯联盟（Solaris United）赏金任务"""
    async for result in _render_syndicate(event, SyndicateEnum.SolarisSyndicate, "索拉里斯联盟"):
        yield result
