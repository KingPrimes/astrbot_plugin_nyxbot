"""wf_market_liches - 赤毒巫妖 & 信条姐妹拍卖指令

指令:
  /CD  or  /赤毒  or  /cd  → 查询 Market 赤毒巫妖拍卖
  /XT  or  /信条  or  /xt  → 查询 Market 信条姐妹拍卖
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, MessageEventResult

from ...registry import wf
from ..init import init_ready
from ..render.card_market_lich_sister import render_market_lich_sister_card
from ..render.card_market_orders import render_market_orders_possible_items_card
from ..render.card_renderer import CardRenderer
from ..service.market import MarketService


async def _handle_lich_sister(
    event: AstrMessageEvent, keyword: str, search_type: str, title_suffix: str
) -> AsyncGenerator[MessageEventResult, None]:
    """通用赤毒/信条拍卖处理。"""

    if not keyword:
        yield event.plain_result(f"请输入武器名称！用法：/{title_suffix} 武器名称")
        return

    try:
        result = await MarketService.search_market_lich_sister(
            keyword.strip(), search_type
        )
    except Exception:
        logger.exception(f"查询{title_suffix}拍卖失败")
        yield event.plain_result(f"查询{title_suffix}拍卖失败，请检查名称是否正确或稍后重试")
        return

    if result is None:
        yield event.plain_result(f"未找到匹配的{title_suffix}武器: {keyword}")
        return

    if isinstance(result, tuple):
        if result[1] is None:
            # possible_items
            items = result[0]
            if not isinstance(items, list) or not items:
                yield event.plain_result(f"未找到匹配的{title_suffix}武器: {keyword}")
                return
            chain = await CardRenderer.render_card_to_chain_result(
                render_market_orders_possible_items_card, items
            )
        else:
            chain = await CardRenderer.render_card_to_chain_result(
                render_market_lich_sister_card, result[1], title_suffix
            )
    else:
        yield event.plain_result(f"未找到匹配的{title_suffix}武器: {keyword}")
        return

    yield event.chain_result(chain)


@wf.command("CD",alias=["cd","赤毒"])
async def wf_market_liches(self, event: AstrMessageEvent, keyword: str = "") -> AsyncGenerator[MessageEventResult, None]:
    await init_ready()
    async for r in _handle_lich_sister(event, keyword, "lich", "赤毒"):
        yield r


@wf.command("XT",alias=["xt","信条"])
async def wf_market_sisters(self, event: AstrMessageEvent, keyword: str = "") -> AsyncGenerator[MessageEventResult, None]:
    await init_ready()
    async for r in _handle_lich_sister(event, keyword, "sister", "信条"):
        yield r
