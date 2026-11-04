"""wf_whisper - /w <序号> 获取市场私聊语句

用法::

    /w        → 用法提示
    /w 3      → 回复上一张卡片第 3 条的私聊语句

序号来自 ``/WM`` ``/WR`` ``/CD`` ``/XT`` 价格卡片最左列，2 分钟内有效。
语句可直接粘贴到游戏聊天框联系卖家。
"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..init import init_ready
from ..service import whisper as whisper_service
from ..util.command_args import command_args


@wf.command("w", alias=["私聊", "whisper"])
async def wf_whisper(self, event: AstrMessageEvent):
    """获取市场卡片的私聊语句（可直接粘贴到游戏内）。"""
    await init_ready()

    raw = command_args(event, "w", "私聊", "whisper")
    session = event.unified_msg_origin
    sender = str(event.get_sender_id() or "")
    yield event.plain_result(whisper_service.reply_for(session, sender, raw))
