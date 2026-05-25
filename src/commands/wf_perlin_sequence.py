"""wf_perlin_sequence - 佩兰数列武器轮换指令

指令:
  /佩兰  or  /佩兰数列  or  /信条武器  → 查看佩兰数列武器轮换信息（TODO stub）
"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent

from ...registry import wf


@wf.command("佩兰",alias=["佩兰数列","信条武器"])
async def wf_perlin_sequence_peilan(self, event: AstrMessageEvent):
    """查看佩兰数列武器轮换信息（暂不实现）"""
    yield event.plain_result("此功能尚未实现，敬请期待")
