"""wf_cycle - /cycle or /平原 - 查看平原周期时间"""
from __future__ import annotations

import astrbot.api.message_components as Comp
from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..render.card_renderer import CardRenderer
from ..service.world_state import WorldStateService


@wf.command("平原")
async def wf_cycle(self, event: AstrMessageEvent):
    """查看所有平原周期（希图斯、金星、扎里曼、魔胎之境）"""
    cycles: list[dict] = []

    # 希图斯（地球）周期
    cetus = await WorldStateService.get_cetus_cycle()
    if cetus:
        cycles.append({
            "name": "🌍 希图斯（地球）",
            "state": "白天" if cetus.is_day else "夜晚",
            "is_day": cetus.is_day,
            "time_left": cetus.time_left,
        })

    # 奥布山谷（金星）周期
    vallis = await WorldStateService.get_vallis_cycle()
    if vallis:
        cycles.append({
            "name": "❄ 金星（奥布山谷）",
            "state": "温暖" if vallis.is_warm else "寒冷",
            "is_day": vallis.is_warm,
            "time_left": vallis.time_left,
        })

    # 扎里曼周期
    zariman = await WorldStateService.get_zariman_cycle()
    if zariman:
        cycles.append({
            "name": "🚀 扎里曼号",
            "state": "Grineer" if zariman.is_corpus else "Corpus",
            "is_day": zariman.is_corpus,
            "time_left": zariman.time_left,
        })

    # 魔胎之境（火卫二）周期
    cambion = await WorldStateService.get_cambion_cycle()
    if cambion:
        is_vome = cambion.active == "VOME"
        cycles.append({
            "name": "🦴 魔胎之境（火卫二）",
            "state": "Vome" if is_vome else "Fass",
            "is_day": is_vome,
            "time_left": cambion.time_left,
        })

    if not cycles:
        yield event.plain_result("无法获取周期数据")
        return

    renderer = CardRenderer()
    img = renderer.create_cycle_card(cycles, "全周期状态")
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
