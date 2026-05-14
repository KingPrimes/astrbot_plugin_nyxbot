"""wf_cycle - /cycle or /平原 - 查看平原周期时间"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent
import astrbot.api.message_components as Comp

from ...registry import wf
from ..service.world_state import WorldStateService
from ..render.card_renderer import CardRenderer


@wf.command("平原")
async def wf_cycle(self, event: AstrMessageEvent):
    """查看所有平原周期（希图斯、金星、扎里曼）"""
    from ..util.time_utils import format_time_remaining_short, parse_wf_timestamp

    cycles = []

    # 希图斯（地球）周期
    cetus = await WorldStateService.get_cetus_cycle()
    if cetus:
        is_day = cetus.get("isDay", cetus.get("is_day", False))
        expiry = parse_wf_timestamp(cetus.get("Expiry", cetus.get("expiry", "")))
        time_left = format_time_remaining_short(expiry) if expiry else ""
        cycles.append({
            "name": "🌍 希图斯（地球）",
            "state": "白天" if is_day else "夜晚",
            "is_day": is_day,
            "time_left": time_left,
        })

    # 金星周期（奥布山谷）
    raw = await WorldStateService.get_raw()
    if raw:
        vallis_raw = raw.get("VallisCycle") or raw.get("VenusCycle")
        if vallis_raw:
            is_warm = vallis_raw.get("isWarm", vallis_raw.get("is_warm", False))
            expiry = parse_wf_timestamp(vallis_raw.get("Expiry", vallis_raw.get("expiry", "")))
            time_left = format_time_remaining_short(expiry) if expiry else ""
            cycles.append({
                "name": "❄ 金星（奥布山谷）",
                "state": "温暖" if is_warm else "寒冷",
                "is_day": is_warm,
                "time_left": time_left,
            })

        # 扎里曼周期
        zariman = raw.get("ZarimanCycle") or raw.get("Zariman")
        if zariman:
            is_void = zariman.get("isCorpus", zariman.get("state", "") == "void")
            expiry = parse_wf_timestamp(zariman.get("Expiry", zariman.get("expiry", "")))
            time_left = format_time_remaining_short(expiry) if expiry else ""
            cycles.append({
                "name": "🚀 扎里曼号",
                "state": "虚空" if is_void else "Corpus",
                "is_day": is_void,
                "time_left": time_left,
            })

        # 魔胎之境（火卫二）周期
        deimos = raw.get("CambionCycle") or raw.get("DeimosCycle")
        if deimos:
            state = deimos.get("Active", deimos.get("state", ""))
            is_vome = state in ("vome", "VOME", True) if isinstance(state, (bool, str)) else False
            expiry = parse_wf_timestamp(deimos.get("Expiry", deimos.get("expiry", "")))
            time_left = format_time_remaining_short(expiry) if expiry else ""
            cycles.append({
                "name": "🦴 魔胎之境（火卫二）",
                "state": "Vome" if is_vome else "Fass",
                "is_day": is_vome,
                "time_left": time_left,
            })

    if not cycles:
        yield event.plain_result("无法获取周期数据")
        return

    renderer = CardRenderer()
    img = renderer.create_cycle_card(cycles, "全周期状态")
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
