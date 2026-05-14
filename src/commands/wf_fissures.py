"""wf_fissures - /fissures or /裂隙 - 查看当前裂隙"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent
import astrbot.api.message_components as Comp

from ...registry import wf
from ..service.world_state import WorldStateService
from ..render.card_renderer import CardRenderer


# 裂隙等级名称映射
TIER_NAMES = {1: "Lith 不朽", 2: "Meso 无瑕", 3: "Neo 光辉", 4: "Axi 幻影"}


@wf.command("裂隙")
async def wf_fissures(self, event: AstrMessageEvent):
    """查看当前裂隙"""
    fissures_raw = await WorldStateService.get_fissures()

    if not fissures_raw:
        yield event.plain_result("当前没有活跃的裂隙")
        return

    from ..util.time_utils import format_time_remaining_short, parse_wf_timestamp

    fissures = []
    for f in fissures_raw:
        node = f.get("Node", f.get("node", "未知"))
        mission_type = f.get("MissionType", f.get("mission_type", "未知"))
        faction = f.get("Faction", f.get("faction", ""))
        tier = f.get("Tier", f.get("tier", 0))
        tier_name = TIER_NAMES.get(tier, f"Tier {tier}")
        expiry = parse_wf_timestamp(f.get("Expiry", f.get("expiry", "")))
        eta = format_time_remaining_short(expiry) if expiry else ""

        fissures.append({
            "node": node,
            "mission_type": mission_type,
            "faction": faction,
            "tier": tier,
            "tier_name": tier_name,
            "eta": eta,
        })

    if not fissures:
        yield event.plain_result("当前没有活跃的裂隙")
        return

    renderer = CardRenderer()
    img = renderer.create_fissure_card(fissures)
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])

