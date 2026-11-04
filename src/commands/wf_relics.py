"""wf_relics - /遗物 - 查询遗物数据（按名称或奖励物品搜索）"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..init import init_ready
from ..render.card_relics import render_relic_card, render_relic_help_card
from ..render.card_renderer import CardRenderer
from ..service.relics import RelicsService
from ..util.command_args import command_args
from ..util.search_index import fuzzy_pinyin, normalize_key

_RELIC_RENDER_LIMIT = 30
"""单次最多画 30 个遗物。只给档位时会命中上百条，因此档位查询直接拒绝。"""

_RELIC_TIERS = ("古纪", "前纪", "中纪", "后纪", "安魂")
"""遗物档位。单独出现时说明用户还没指明具体是哪个遗物。"""

_TIER_PINYIN = frozenset(
    fuzzy_pinyin(p) for p in ("zhongji", "houji", "guji", "qianji", "anhun")
)
"""档位的拼音写法，`/遗物 zhongji` 同样视为没指定遗物。"""


def _tier_only(name: str) -> bool:
    """输入是否只给了档位（`中纪`、`中纪 遗物`、`zhongji`）。"""
    key = " ".join((name or "").split()).replace("遗物", "").strip()
    if not key:
        return False
    return key in _RELIC_TIERS or fuzzy_pinyin(normalize_key(key)) in _TIER_PINYIN


@wf.command(name="遗物", alias=["核桃"])
async def wf_relics(self, event: AstrMessageEvent):
    """查询遗物数据 — 支持按遗物名称或奖励物品搜索。

    用法: /遗物 <搜索词>  或  /核桃 <搜索词>
    示例:
      /遗物 中纪 A1      → 精确查这个遗物
      /遗物 Frost Prime  → 搜索奖励含"Frost Prime"的遗物
    """
    await init_ready()

    # 遗物名/奖励名可能含空格（"中纪 A1"、"Frost Prime"），取整段原文
    name = command_args(event, "遗物", "核桃")

    # 没有参数 → 出使用说明图
    if not name:
        result = await CardRenderer.render_card_to_chain_result(
            render_relic_help_card
        )
        yield event.chain_result(result)
        return

    # 只写档位等于没指定遗物：中纪 196 个、后纪 198 个，画出来没意义
    if _tier_only(name):
        yield event.plain_result(
            f"「{name.strip()}」只给出了档位，请补上遗物编号，例如：\n"
            "  /遗物 中纪 A1\n"
            "  /遗物 后纪 S5\n"
            "也可以按奖励物品查：/遗物 Frost Prime"
        )
        return

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
