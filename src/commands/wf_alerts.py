"""wf_alerts - /alerts or /警报 - 查看当前警报"""
from __future__ import annotations

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..config.config import get_qq_markdown_enabled
from ..markdown.alerts import format_alerts_markdown
from ..render.card_alert import render_alert_card
from ..render.card_renderer import CardRenderer
from ..service.world_state import WorldStateService
from ..util.markdown_utils import is_qq_official


@wf.command("警报")
async def wf_alerts(self, event: AstrMessageEvent):
    """查看当前警报"""
    alerts = await WorldStateService.get_alerts()
    logger.info(f"Alerts数据：{len(alerts)} 个")
    if not alerts:
        yield event.plain_result("当前没有活跃的警报")
        return

    if is_qq_official(event) and get_qq_markdown_enabled():
        yield event.plain_result(format_alerts_markdown(alerts))
    else:
        result = await CardRenderer.render_card_to_chain_result(
            render_alert_card, alerts
        )
        yield event.chain_result(result)
