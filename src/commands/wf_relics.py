"""wf_relics - /遗物 - 查询遗物数据（按名称或奖励物品搜索）"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..init import init_ready
from ..render.card_relics import render_relic_card
from ..render.card_renderer import CardRenderer
from ..service.relics import RelicsService
from ..util.command_args import command_args

_RELIC_RENDER_LIMIT = 30
"""单次最多画 30 个遗物。`/遗物 中纪` 有 196 条，全画是 1.9 万像素高、1.4 秒的图。"""


@wf.command(name="遗物", alias=["核桃"])
async def wf_relics(self, event: AstrMessageEvent):
    """查询遗物数据 — 支持按遗物名称或奖励物品搜索。

    用法: /遗物 <搜索词>  或  /核桃 <搜索词>
    示例:
      /遗物              → 显示所有遗物
      /遗物 中纪 A1      → 搜索遗物名/奖励含 "中纪 A1" 的记录
      /遗物 Frost Prime  → 搜索奖励含"Frost Prime"的遗物
    """
    await init_ready()

    # 遗物名/奖励名可能含空格（"中纪 A1"、"Frost Prime"），取整段原文
    name = command_args(event, "遗物", "核桃")

    relics = await RelicsService.find_by_name_or_reward(name)

    if not relics:
        yield event.plain_result(
            f"未找到与 '{name}' 相关的遗物" if name
            else "遗物数据为空，请先执行数据同步"
        )
        return

    total = len(relics)
    shown = relics[:_RELIC_RENDER_LIMIT]

    result = await CardRenderer.render_card_to_chain_result(render_relic_card, shown)
    yield event.chain_result(result)

    if total > len(shown):
        yield event.plain_result(
            f"共 {total} 个遗物，仅显示前 {len(shown)} 个；"
            "加档位或奖励名可缩小范围（如 /遗物 中纪 A1）"
        )
