"""wf_relics - /relics or /遗物 - 查看当前遗物掉落"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..service.world_state import WorldStateService
from ..render.card_renderer import CardRenderer


@wf.command("遗物")
async def wf_relics(self, event: AstrMessageEvent):
    """查看当前遗物掉落"""
    # 直接从 raw 数据获取遗物信息
    raw = await WorldStateService.get_raw()

    if not raw:
        yield event.plain_result("无法获取遗物数据")
        return

    relics_raw = raw.get("Relics", raw.get("relics", []))
    if not relics_raw:
        yield event.plain_result("当前没有遗物掉落数据")
        return

    from ..util.time_utils import format_time_remaining_short, parse_wf_timestamp

    relics = []
    for r in relics_raw:
        name = r.get("ItemType", r.get("item_type", ""))
        if "/" in str(name):
            name = str(name).split("/")[-1].replace("_", " ")
        tier = r.get("Tier", r.get("tier", ""))
        relic_name = r.get("RelicName", r.get("relic_name", ""))
        expiry = parse_wf_timestamp(r.get("Expiry", r.get("expiry", "")))
        eta = format_time_remaining_short(expiry) if expiry else ""

        relics.append({
            "name": name,
            "tier": tier,
            "relic_name": relic_name,
            "eta": eta,
        })

    renderer = CardRenderer()
    img = renderer.create_relic_card(relics)
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.image_result(img_bytes)
