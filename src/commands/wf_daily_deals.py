"""wf_daily_deals - /deals or /每日特惠 - 查看达尔沃每日特惠"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..config.config import get_qq_markdown_enabled
from ..markdown.daily_deals import format_daily_deals_markdown
from ..render.card_daily_deals import render_daily_deals_card
from ..render.card_renderer import CardRenderer
from ..service.world_state import WorldStateService
from ..util.markdown_utils import is_qq_official


@wf.command("每日特惠")
async def wf_daily_deals(self, event: AstrMessageEvent):
    """查看达尔沃的每日特惠商品"""
    deals = await WorldStateService.get_daily_deals()

    if not deals:
        yield event.plain_result("当前没有每日特惠数据")
        return

    if is_qq_official(event) and get_qq_markdown_enabled():
        yield event.plain_result(format_daily_deals_markdown(deals))
    else:
        result = await CardRenderer.render_card_to_chain_result(
            render_daily_deals_card, deals
        )
        yield event.chain_result(result)
