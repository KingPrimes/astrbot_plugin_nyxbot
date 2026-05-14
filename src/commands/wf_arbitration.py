"""wf_arbitration - /arbitration or /仲裁 - 查看当前仲裁"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent
import astrbot.api.message_components as Comp

from ...registry import wf
from ..service.world_state import WorldStateService
from ..render.card_renderer import CardRenderer


@wf.command("仲裁")
async def wf_arbitration(self, event: AstrMessageEvent):
    """查看当前仲裁任务"""
    arb_raw = await WorldStateService.get_arbitration()

    if not arb_raw:
        yield event.plain_result("当前没有活跃的仲裁任务")
        return

    from ..util.time_utils import format_time_remaining_short, parse_wf_timestamp

    node = arb_raw.get("Node", arb_raw.get("node", "未知节点"))
    mission_type = arb_raw.get("Type", arb_raw.get("mission_type", "未知"))
    faction = arb_raw.get("Faction", arb_raw.get("faction", "未知"))
    expiry = parse_wf_timestamp(arb_raw.get("Expiry", arb_raw.get("expiry", "")))
    eta = format_time_remaining_short(expiry) if expiry else ""

    arbitration = {
        "node": node,
        "mission_type": mission_type,
        "faction": faction,
        "eta": eta,
    }

    renderer = CardRenderer()
    img = renderer.create_arbitration_card(arbitration)
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
