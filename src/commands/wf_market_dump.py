"""wf_market_god_dump - 金垃圾指令

指令:
  /金垃圾  → 查询 Warframe.Market 杜卡德金币（100 杜卡德物品）
"""
from __future__ import annotations

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..init import init_ready
from ..render.card_market_ducats import render_market_ducats_card
from ..render.card_renderer import CardRenderer
from ..service.market_ducats import MarketDucatsService


async def _dump_handler(
    event: AstrMessageEvent, fetch_method, title: str
):
    """通用垃圾 dump 处理器 — 获取数据、渲染卡片、返回图片。"""
    await init_ready()

    try:
        day_items, hour_items = await fetch_method()
    except Exception:
        logger.exception(f"获取{title}数据失败")
        yield event.plain_result(f"获取{title}数据失败，请稍后重试")
        return

    if not day_items and not hour_items:
        yield event.plain_result(f"当前没有{title}数据")
        return

    result = await CardRenderer.render_card_to_chain_result(
        render_market_ducats_card, day_items, hour_items, title
    )
    yield event.chain_result(result)


@wf.command("金垃圾")
async def wf_market_god_dump(self, event: AstrMessageEvent):
    """查询 Warframe.Market 杜卡德金币（100 杜卡德物品）"""

    async for result in _dump_handler(
        event, MarketDucatsService.get_gold_dump, "金垃圾"
    ):
        yield result


@wf.command("银垃圾")
async def wf_market_silver_dump(self, event: AstrMessageEvent):
    """查询 Warframe.Market 杜卡德银币（45-99 杜卡德物品）"""

    async for result in _dump_handler(
        event, MarketDucatsService.get_silver_dump, "银垃圾"
    ):
        yield result

