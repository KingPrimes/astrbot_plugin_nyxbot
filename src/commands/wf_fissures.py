"""wf_fissures - /fissures or /裂隙 - 查看当前裂隙"""
from __future__ import annotations

import astrbot.api.message_components as Comp
from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..model.world_state import ActiveMission, VoidStorms
from ..render.card_renderer import CardRenderer
from ..service.world_state import WorldStateService

# 裂隙等级名称映射
TIER_NAMES = {1: "Lith 不朽", 2: "Meso 无瑕", 3: "Neo 光辉", 4: "Axi 幻影"}


def _tier_num(enum_val) -> int:
    """从 VoidEnum 名称中提取裂隙等级数字 / Extract tier number from VoidEnum name.

    VoidEnum 成员如 VoidT1=1, VoidT2=2, VoidT3=3, VoidT4=4。
    """
    if enum_val is None:
        return 0
    name = enum_val.name if hasattr(enum_val, "name") else str(enum_val)
    for t in (4, 3, 2, 1):
        if f"VoidT{t}" in name or name == f"T{t}":
            return t
    return 0


@wf.command("裂隙")
async def wf_fissures(self, event: AstrMessageEvent):
    """查看当前裂隙"""
    fissures_raw = await WorldStateService.get_fissures()

    if not fissures_raw:
        yield event.plain_result("当前没有活跃的裂隙")
        return

    fissures: list[dict] = []
    for f in fissures_raw:
        if isinstance(f, ActiveMission):
            tier_enum = f.modifier
            tier = _tier_num(tier_enum)
            tier_name = TIER_NAMES.get(tier, f"Tier {tier}")
            node = f.node or "未知"
            mission_type = f.mission_type.name if f.mission_type else "未知"
            faction = f.faction.name if f.faction else ""
            eta = f.time_left
        elif isinstance(f, VoidStorms):
            tier_enum = f.tier
            tier = _tier_num(tier_enum)
            tier_name = TIER_NAMES.get(tier, f"Tier {tier}")
            node = f.node or "未知"
            mission_type = "Railjack"
            faction = ""
            eta = f.time_left
        else:
            continue

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


