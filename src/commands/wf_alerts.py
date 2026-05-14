"""wf_alerts - /alerts or /警报 - 查看当前警报"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent
import astrbot.api.message_components as Comp

from ...registry import wf
from ..service.world_state import WorldStateService
from ..render.card_renderer import CardRenderer


@wf.command("警报")
async def wf_alerts(self, event: AstrMessageEvent):
    """查看当前警报"""
    alerts_raw = await WorldStateService.get_alerts()

    if not alerts_raw:
        yield event.plain_result("当前没有活跃的警报")
        return

    # 转换为渲染器所需的数据格式
    alerts = []
    for a in alerts_raw:
        mission = a.get("Mission", a.get("mission", {}))
        reward = a.get("Reward", a.get("reward", {}))
        items = []
        if "countedItems" in reward:
            for ci in reward["countedItems"]:
                if "ItemType" in ci:
                    items.append(ci["ItemType"].split("/")[-1].replace("_", " "))
        if "items" in reward:
            items.extend(reward["items"])

        from ..util.time_utils import format_time_remaining_short, parse_wf_timestamp

        expiry = parse_wf_timestamp(a.get("Expiry", a.get("expiry", "")))
        eta = format_time_remaining_short(expiry) if expiry else ""

        node = mission.get("Node", mission.get("node", "未知"))
        mission_type = mission.get("Type", mission.get("mission_type", "未知"))
        faction = mission.get("Faction", mission.get("faction", "未知"))
        min_lv = mission.get("MinEnemyLevel", mission.get("min_enemy_level", 0))
        max_lv = mission.get("MaxEnemyLevel", mission.get("max_enemy_level", 0))

        alerts.append({
            "node": node,
            "mission_type": mission_type,
            "faction": faction,
            "min_level": min_lv,
            "max_level": max_lv,
            "rewards": items[:6],
            "eta": eta,
        })

    renderer = CardRenderer()
    img = renderer.create_alert_card(alerts)
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
