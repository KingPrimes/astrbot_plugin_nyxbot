"""wf_riven_dis_update - 紫卡倾向变动指令

指令:
  /紫卡倾向变动  or  /倾向变动  → 查看武器紫卡倾向变动（TODO stub）
"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent

from ...registry import wf


@wf.command("紫卡倾向变动")
async def wf_riven_dis_update(self, event: AstrMessageEvent):
    """查看武器紫卡倾向变动（暂不实现）"""
    yield event.plain_result("此功能尚未实现，敬请期待")


@wf.command("倾向变动")
async def wf_riven_dis_update_short(self, event: AstrMessageEvent):
    """查看武器紫卡倾向变动（暂不实现，别名）"""
    yield event.plain_result("此功能尚未实现，敬请期待")
