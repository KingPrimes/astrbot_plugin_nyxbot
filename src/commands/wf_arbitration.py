"""wf_arbitration - /arbitration or /仲裁 - 查看当前仲裁"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent

from ...registry import wf


@wf.command("仲裁")
async def wf_arbitration(self, event: AstrMessageEvent):
    """查看当前仲裁任务（暂不实现）。"""
    yield event.plain_result("当前没有活跃的仲裁任务")
