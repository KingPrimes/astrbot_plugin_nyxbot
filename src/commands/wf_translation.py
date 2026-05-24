"""wf_translation - 翻译指令

指令:
  /翻译  → 翻译 Warframe 术语（TODO stub）
"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent

from ...registry import wf


@wf.command("翻译")
async def wf_translation(self, event: AstrMessageEvent):
    """翻译 Warframe 术语（暂不实现）"""
    yield event.plain_result("此功能尚未实现，敬请期待")
