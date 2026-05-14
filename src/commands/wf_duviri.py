"""wf_duviri - /duviri or /双衍 - 查看双衍王境周期"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent
import astrbot.api.message_components as Comp

from ...registry import wf
from ..service.world_state import WorldStateService
from ..render.card_renderer import CardRenderer


@wf.command("双衍")
async def wf_duviri(self, event: AstrMessageEvent):
    """查看双衍王境周期"""
    duviri_raw = await WorldStateService.get_duviri_cycle()

    if not duviri_raw:
        yield event.plain_result("无法获取双衍王境数据")
        return

    from ..util.time_utils import format_time_remaining_short, parse_wf_timestamp

    state = duviri_raw.get("state", duviri_raw.get("State", ""))
    is_day = duviri_raw.get("isDay", duviri_raw.get("is_day", False))
    expiry = parse_wf_timestamp(duviri_raw.get("Expiry", duviri_raw.get("expiry", "")))
    time_left = format_time_remaining_short(expiry) if expiry else ""
    spiral = duviri_raw.get("spiral", duviri_raw.get("Spiral", ""))
    commander = duviri_raw.get("commander", duviri_raw.get("Commander", ""))

    duviri = {
        "state": state,
        "is_day": is_day,
        "time_left": time_left,
        "spiral": spiral,
        "commander": commander,
    }

    renderer = CardRenderer()
    img = renderer.create_duviri_card(duviri)
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])

