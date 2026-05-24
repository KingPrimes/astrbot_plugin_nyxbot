"""wf_market_riven - Market 紫卡拍卖指令

指令:
  /WR  or  /wr  → 查询 Warframe.Market 紫卡拍卖
"""
from __future__ import annotations

import astrbot.api.message_components as Comp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from ...registry import wf


@wf.command("WR")
async def wf_market_riven(self, event: AstrMessageEvent, keyword: str = ""):
    """查询 Warframe.Market 紫卡拍卖"""
    from ..render.card_renderer import CardRenderer
    from ..service.market import MarketService

    if not keyword:
        yield event.plain_result("请输入武器名称！用法：/WR 武器名称")
        return

    try:
        result = await MarketService.search_market_riven(keyword.strip())
    except Exception:
        logger.exception("查询紫卡拍卖失败")
        yield event.plain_result("查询紫卡拍卖失败，请检查名称是否正确或稍后重试")
        return

    if result is None:
        yield event.plain_result(f"未找到匹配的紫卡武器: {keyword}")
        return

    renderer = CardRenderer()
    img = renderer.create_market_riven_card(result)
    img_bytes = renderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])


@wf.command("wr")
async def wf_market_riven_lower(self, event: AstrMessageEvent, keyword: str = ""):
    """查询 Warframe.Market 紫卡拍卖（别名）"""
    async for r in wf_market_riven(self, event, keyword):
        yield r
