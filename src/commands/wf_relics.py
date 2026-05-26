"""wf_relics - /遗物 - 查询遗物数据（按名称或奖励物品搜索）"""
from __future__ import annotations

import asyncio

import astrbot.api.message_components as Comp
from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..init import init_ready
from ..render.card_relics import render_relic_card
from ..render.card_renderer import CardRenderer
from ..service.relics import RelicsService


@wf.command(name="遗物", alias=["核桃"])
async def wf_relics(self, event: AstrMessageEvent, name: str = ""):
    """查询遗物数据 — 支持按遗物名称或奖励物品搜索。

    用法: /遗物 <搜索词>  或  /核桃 <搜索词>
    示例:
      /遗物              → 显示所有遗物
      /遗物 丽斯         → 搜索名称含"丽斯"的遗物
      /遗物 Frost Prime  → 搜索奖励含"Frost Prime"的遗物
    """
    await init_ready()

    relics = await RelicsService.find_by_name_or_reward(name)

    if not relics:
        yield event.plain_result(
            f"未找到与 '{name}' 相关的遗物" if name
            else "遗物数据为空，请先执行数据同步"
        )
        return

    renderer = CardRenderer()
    loop = asyncio.get_running_loop()
    img_bytes = await loop.run_in_executor(
        None,
        lambda: CardRenderer.render_to_bytes(render_relic_card(renderer, relics)),
    )
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
