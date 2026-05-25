"""wf_market_god_dump - 金垃圾指令

指令:
  /金垃圾  → 查询 Warframe.Market 杜卡德金币（100 杜卡德物品）
"""
from __future__ import annotations

import astrbot.api.message_components as Comp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from ...registry import wf


@wf.command("金垃圾")
async def wf_market_god_dump(self, event: AstrMessageEvent):
    """查询 Warframe.Market 杜卡德金币（100 杜卡德物品）"""
    from ..render.card_renderer import CardRenderer
    from ..service.market_ducats import MarketDucatsService

    try:
        day_items, hour_items = await MarketDucatsService.get_gold_dump()
    except Exception:
        logger.exception("获取金垃圾数据失败")
        yield event.plain_result("获取金垃圾数据失败，请稍后重试")
        return

    if not day_items and not hour_items:
        yield event.plain_result("当前没有金垃圾数据")
        return

    from ..render.card_market_ducats import render_market_ducats_card

    renderer = CardRenderer()
    img = render_market_ducats_card(renderer, day_items, hour_items, "金垃圾")
    img_bytes = renderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])

@wf.command("银垃圾")
async def wf_market_silver_dump(self, event: AstrMessageEvent):
    """查询 Warframe.Market 杜卡德银币（45-99 杜卡德物品）"""
    from ..render.card_renderer import CardRenderer
    from ..service.market_ducats import MarketDucatsService

    try:
        day_items, hour_items = await MarketDucatsService.get_silver_dump()
    except Exception:
        logger.exception("获取银垃圾数据失败")
        yield event.plain_result("获取银垃圾数据失败，请稍后重试")
        return

    if not day_items and not hour_items:
        yield event.plain_result("当前没有银垃圾数据")
        return

    from ..render.card_market_ducats import render_market_ducats_card

    renderer = CardRenderer()
    img = render_market_ducats_card(renderer, day_items, hour_items, "银垃圾")
    img_bytes = renderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])

