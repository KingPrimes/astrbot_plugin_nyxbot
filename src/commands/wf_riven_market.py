"""wf_riven_market - Riven Market 紫卡拍卖指令

指令:
  /RM  or  /rm  → 查询 Riven Market 市场拍卖的紫卡（TODO stub）
"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..init import init_ready


@wf.command("RM",alias=["rm"])
async def wf_riven_market(self, event: AstrMessageEvent):
    """查询 Riven Market 市场拍卖的紫卡（暂不实现）"""
    await init_ready()
    yield event.plain_result("此功能尚未实现，敬请期待")
