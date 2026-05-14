"""wf_nightwave - /nightwave or /电波 - 查看午夜电波"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent
import astrbot.api.message_components as Comp

from ...registry import wf
from ..service.world_state import WorldStateService
from ..render.card_renderer import CardRenderer


@wf.command("电波")
async def wf_nightwave(self, event: AstrMessageEvent):
    """查看午夜电波"""
    nw_raw = await WorldStateService.get_nightwave()

    if not nw_raw:
        yield event.plain_result("无法获取午夜电波数据")
        return

    season = nw_raw.get("Season", nw_raw.get("season", ""))
    rank = nw_raw.get("Rank", nw_raw.get("rank", 0))
    challenges_raw = nw_raw.get("Challenges", nw_raw.get("challenges", []))

    challenges = []
    for c in challenges_raw:
        title = c.get("Title", c.get("title", "未知任务"))
        standing = c.get("Standing", c.get("standing", 0))
        is_daily = c.get("IsDaily", c.get("is_daily", False))
        is_elite = c.get("IsElite", c.get("is_elite", False))

        challenges.append({
            "title": title,
            "standing": standing,
            "is_daily": is_daily,
            "is_elite": is_elite,
        })

    nightwave = {
        "season": season,
        "rank": rank,
        "challenges": challenges,
    }

    renderer = CardRenderer()
    img = renderer.create_nightwave_card(nightwave)
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
