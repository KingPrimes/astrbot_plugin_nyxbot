"""wf_daily_deals - /deals or /每日特惠 - 查看达尔沃每日特惠"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent
import astrbot.api.message_components as Comp

from ...registry import wf
from ..service.world_state import WorldStateService
from ..render.card_renderer import CardRenderer


@wf.command("每日特惠")
async def wf_daily_deals(self, event: AstrMessageEvent):
    """查看达尔沃的每日特惠商品"""
    deals_raw = await WorldStateService.get_daily_deals()

    if not deals_raw:
        yield event.plain_result("当前没有每日特惠数据")
        return

    deals = []
    for d in deals_raw:
        item_name = d.get("StoreItem", d.get("item", ""))
        if "/" in str(item_name):
            item_name = str(item_name).split("/")[-1].replace("_", " ")
        original = d.get("OriginalPrice", d.get("original_price", 0))
        sale = d.get("SalePrice", d.get("sale_price", 0))
        discount = d.get("Discount", d.get("discount", 0))
        total = d.get("Total", d.get("total", 0))
        sold = d.get("Sold", d.get("sold", 0))

        deals.append({
            "item": item_name,
            "original_price": original,
            "sale_price": sale,
            "discount": discount,
            "total": total,
            "sold": sold,
        })

    renderer = CardRenderer()
    img = renderer.create_daily_deals_card(deals)
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
