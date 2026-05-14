"""wf_void_trader - /void or /奸商 - 查看虚空商人"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent
import astrbot.api.message_components as Comp

from ...registry import wf
from ..service.world_state import WorldStateService
from ..render.card_renderer import CardRenderer


@wf.command("奸商")
async def wf_void_trader(self, event: AstrMessageEvent):
    """查看虚空商人（Baro Ki'Teer）"""
    trader_raw = await WorldStateService.get_void_trader()

    if not trader_raw:
        yield event.plain_result("虚空商人未找到数据")
        return

    from ..util.time_utils import format_time_remaining_short, parse_wf_timestamp

    name = trader_raw.get("Character", trader_raw.get("name", "Baro Ki'Teer"))
    location = trader_raw.get("Location", trader_raw.get("location", "未知中继站"))
    expiry = parse_wf_timestamp(trader_raw.get("Expiry", trader_raw.get("expiry", "")))
    eta = format_time_remaining_short(expiry) if expiry else ""

    # 商品列表
    inventory_raw = trader_raw.get("Manifest", trader_raw.get("inventory", []))
    inventory = []
    for item in inventory_raw:
        item_name = item.get("ItemType", item.get("name", ""))
        if "/" in str(item_name):
            item_name = str(item_name).split("/")[-1].replace("_", " ")
        ducats = item.get("PrimePrice", item.get("ducats", 0))
        credits = item.get("RegularPrice", item.get("credits", 0))
        inventory.append({
            "name": item_name,
            "ducats": ducats,
            "credits": credits,
        })

    trader = {
        "name": name,
        "location": location,
        "eta": eta,
        "inventory": inventory,
    }

    renderer = CardRenderer()
    img = renderer.create_void_trader_card(trader)
    img_bytes = CardRenderer.render_to_bytes(img)
    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
