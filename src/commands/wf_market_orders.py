"""wf_market_orders - Market 市场订单查询指令

指令:
  /WM  or  /市场  or  /wm  or  /market  → 查询 Warframe.Market 物品订单

支持参数:
  满级 | MAX  → 仅查询满级物品
  购买 | 买家 | BUY   → 查询买家报价
  出售 | 卖家 | SELL  → 查询卖家报价
  PC | PS4 | XBOX | SWITCH  → 指定平台
"""
from __future__ import annotations

import astrbot.api.message_components as Comp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from ...registry import wf


def _parse_params(text: str) -> tuple[str, str, bool, bool]:
    """解析订单查询参数。

    Returns:
        (keyword, platform, is_by, is_max)
    """
    processed = text.strip().upper()
    platform = "pc"
    is_by = False  # False=出售(SELL), True=购买(BUY)
    is_max = False

    # 平台检测
    for p in ["PC", "PS4", "XBOX", "SWITCH"]:
        if p in processed:
            platform = p.lower()
            processed = processed.replace(p, "")
            break

    # 满级
    if "满级" in processed or "MAX" in processed:
        is_max = True
        processed = processed.replace("满级", "").replace("MAX", "")

    # 买卖
    if "购买" in processed or "买家" in processed or "BUY" in processed:
        is_by = True
        processed = processed.replace("购买", "").replace("买家", "").replace("BUY", "")
    elif "出售" in processed or "卖家" in processed or "SELL" in processed:
        is_by = False
        processed = processed.replace("出售", "").replace("卖家", "").replace("SELL", "")

    # 去掉指令前缀
    for prefix in ["/WM", "/市场", "/WM", "WM", "/MARKET", "MARKET"]:
        processed = processed.replace(prefix, "")
    keyword = processed.strip()

    return keyword, platform, is_by, is_max


@wf.command(name="WM", alias=["市场", "wm", "market"])
async def wf_market_orders(self, event: AstrMessageEvent, keyword: str = ""):
    """查询 Warframe.Market 物品订单"""
    from ..render.card_renderer import CardRenderer
    from ..service.market import MarketService

    if not keyword:
        yield event.plain_result("请输入正确的名称！用法：/WM 物品名称 [满级|MAX] [购买|出售] [PC|PS4|XBOX|SWITCH]")
        return

    kw, platform, is_by, is_max = _parse_params(keyword)
    if not kw:
        yield event.plain_result("请输入正确的名称！")
        return

    try:
        result = await MarketService.search_market_orders(kw, platform, is_by, is_max)
    except Exception:
        logger.exception("查询市场订单失败")
        yield event.plain_result("查询市场订单失败，请检查名称是否正确或稍后重试")
        return

    if result is None:
        yield event.plain_result(f"未找到匹配的物品: {kw}")
        return

    from ..render.card_market_orders import (
        render_market_orders_card,
        render_market_orders_possible_items_card,
    )

    renderer = CardRenderer()
    if isinstance(result, tuple) and result[1] is None:
        # possible_items 列表
        possible_items = result[0]
        if not possible_items:
            yield event.plain_result(f"未找到匹配的物品: {kw}")
            return
        img = render_market_orders_possible_items_card(renderer, possible_items)
    else:
        img = render_market_orders_card(renderer, result)

    img_bytes = renderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
