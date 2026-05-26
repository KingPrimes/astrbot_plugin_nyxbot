"""wf_market_riven - Market 紫卡拍卖指令

指令:
  /WR  or  /wr  → 查询 Warframe.Market 紫卡拍卖

用法:
  /WR 武器名                              # 基础查询
  /WR 武器名 暴击率,暴击伤害                # 多参数：正面词条
  /WR 武器名 暴击率,暴击伤害 无              # 多参数：正面 + 负面词条
  /WR 武器名-暴击率,暴击伤害                # Java 风格：以 `-` 分隔
  /WR 武器名-暴击率,暴击伤害-无              # Java 风格：正面 + 负面词条
"""
from __future__ import annotations

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..init import init_ready
from ..render.card_market_riven import render_market_riven_card
from ..render.card_renderer import CardRenderer
from ..service.market_riven import MarketRivenService


@wf.command("WR", alias=["wr"])
async def wf_market_riven(
    self,
    event: AstrMessageEvent,
    keyword: str = "",
    positive_stats: str = "",
    negative_stats: str = "",
):
    """查询 Warframe.Market 紫卡拍卖。

    Args:
        keyword: 武器名称（可含 `-` 分隔的正面/负面词条）。
        positive_stats: 正面词条（逗号分隔，支持中文逗号）。
        negative_stats: 负面词条限定（"有"/"无"）。
    """
    await init_ready()

    if not keyword:
        yield event.plain_result(
            "请输入武器名称！用法：\n"
            "  /WR 武器名\n"
            "  /WR 武器名 暴击率,暴击伤害 无\n"
            "  /WR 武器名-暴击率,暴击伤害-无"
        )
        return

    try:
        result = await MarketRivenService.search_market_riven(
            keyword.strip(),
            positive_stats=positive_stats.strip(),
            negative_stats=negative_stats.strip(),
        )
    except Exception:
        logger.exception("查询紫卡拍卖失败")
        yield event.plain_result("查询紫卡拍卖失败，请检查名称是否正确或稍后重试")
        return

    if result is None:
        yield event.plain_result(f"未找到匹配的紫卡武器: {keyword}")
        return

    chain = await CardRenderer.render_card_to_chain_result(
        render_market_riven_card, result
    )
    yield event.chain_result(chain)
