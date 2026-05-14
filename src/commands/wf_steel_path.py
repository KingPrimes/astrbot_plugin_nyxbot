"""wf_steel_path - /steel or /钢铁 - 查看钢铁之路"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent
import astrbot.api.message_components as Comp

from ...registry import wf
from ..service.world_state import WorldStateService
from ..render.card_renderer import CardRenderer


@wf.command("钢铁")
async def wf_steel_path(self, event: AstrMessageEvent):
    """查看钢铁之路"""
    sp_raw = await WorldStateService.get_steel_path()

    if not sp_raw:
        yield event.plain_result("无法获取钢铁之路数据")
        return

    rotation = sp_raw.get("Rotation", sp_raw.get("rotation", ""))
    essences_raw = sp_raw.get("SteelEssence", sp_raw.get("essences", []))

    essences = []
    for e in essences_raw:
        name = e.get("ItemType", e.get("name", ""))
        if "/" in str(name):
            name = str(name).split("/")[-1].replace("_", " ")
        cost = e.get("RegularPrice", e.get("cost", 0))
        essences.append({
            "name": name,
            "cost": cost,
        })

    steel_path = {
        "rotation": rotation,
        "essences": essences,
    }

    renderer = CardRenderer()
    img = renderer.create_steel_path_card(steel_path)
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
