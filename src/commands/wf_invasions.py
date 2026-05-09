"""wf_invasions - /invasions or /入侵 - 查看当前入侵"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..service.world_state import WorldStateService
from ..render.card_renderer import CardRenderer


@wf.command("入侵")
async def wf_invasions(self, event: AstrMessageEvent):
    """查看当前入侵"""
    invasions_raw = await WorldStateService.get_invasions()

    if not invasions_raw:
        yield event.plain_result("当前没有活跃的入侵")
        return

    from ..util.time_utils import format_time_remaining_short, parse_wf_timestamp

    invasions = []
    for inv in invasions_raw:
        node = inv.get("Node", inv.get("node", "未知节点"))

        # 进攻方 vs 防守方
        attacker_info = inv.get("AttackerInfo", inv.get("attacker_info", {}))
        defender_info = inv.get("DefenderInfo", inv.get("defender_info", {}))
        attacker = attacker_info.get("Faction", inv.get("attacker", "未知"))
        defender = defender_info.get("Faction", inv.get("defender", "未知"))

        # 进度
        completion = inv.get("Completion", inv.get("completion", 0))

        # 奖励信息
        attacker_reward = inv.get("AttackerReward", inv.get("attacker_reward", {}))
        defender_reward = inv.get("DefenderReward", inv.get("defender_reward", {}))
        reward_items = []
        for rw in [attacker_reward, defender_reward]:
            items_list = rw.get("countedItems", rw.get("items", []))
            for item in items_list:
                if isinstance(item, dict):
                    name = item.get("ItemType", "").split("/")[-1].replace("_", " ")
                    if name:
                        reward_items.append(name)
                elif isinstance(item, str):
                    reward_items.append(item)

        reward_str = ", ".join(reward_items[:4]) if reward_items else ""

        invasions.append({
            "node": node,
            "attacker": attacker,
            "defender": defender,
            "completion": completion,
            "reward": reward_str,
        })

    renderer = CardRenderer()
    img = renderer.create_invasion_card(invasions)
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.image_result(img_bytes)
