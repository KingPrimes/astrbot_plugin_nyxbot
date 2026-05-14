"""wf_sorties - /sorties or /突击 - 查看今日突击"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent
import astrbot.api.message_components as Comp

from ...registry import wf
from ..service.world_state import WorldStateService
from ..render.card_renderer import CardRenderer


@wf.command("突击")
async def wf_sorties(self, event: AstrMessageEvent):
    """查看今日突击"""
    sorties_raw = await WorldStateService.get_sorties()

    if not sorties_raw:
        yield event.plain_result("当前没有突击数据")
        return

    sortie_data = sorties_raw[0] if isinstance(sorties_raw, list) else sorties_raw
    variants = sortie_data.get("Variants", sortie_data.get("variants", []))

    sorties = []
    for idx, v in enumerate(variants):
        node = v.get("Node", v.get("node", "未知节点"))
        mission_type = v.get("missionType", v.get("mission_type", "未知"))
        modifier = v.get("modifier", v.get("modifierDescription", ""))
        modifier_name = v.get("modifierName", v.get("Modifier", ""))
        faction = v.get("Faction", v.get("faction", ""))

        sorties.append({
            "variant": modifier_name or f"阶段 {idx + 1}",
            "node": node,
            "mission_type": mission_type,
            "modifier": modifier,
            "faction": faction,
        })

    renderer = CardRenderer()
    # 获取派系信息（全局适用）
    boss = sortie_data.get("Boss", sortie_data.get("boss", ""))
    faction = sortie_data.get("Faction", sortie_data.get("faction", ""))
    if faction and not sorties[0].get("faction"):
        for s in sorties:
            s["faction"] = faction

    img = renderer.create_sortie_card(sorties)
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
