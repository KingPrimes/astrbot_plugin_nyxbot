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
    from ..service.market import MarketService

    try:
        day_items, hour_items = await MarketService.get_gold_dump()
    except Exception:
        logger.exception("获取金垃圾数据失败")
        yield event.plain_result("获取金垃圾数据失败，请稍后重试")
        return

    if not day_items and not hour_items:
        yield event.plain_result("当前没有金垃圾数据")
        return

    renderer = CardRenderer()
    img = renderer.create_market_ducats_card(day_items, hour_items, "金垃圾")
    img_bytes = renderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
