"""wf_whisper - /w <序号> 获取市场私聊语句

用法::

    /w        → 用法提示
    /w 3      → 回复上一张卡片第 3 条的私聊语句

序号来自 ``/WM`` ``/WR`` ``/CD`` ``/XT`` 价格卡片最左列，2 分钟内有效。
语句可直接粘贴到游戏聊天框联系卖家。

另有按钮入口（``src/util/whisper_buttons.py`` 生成，id 前缀
``nyxbot:w:``）：MD 版市场卡片底部点击序号按钮 → 直接回复对应私聊
语句，与 ``/w 序号`` 走同一份缓存，等价于少打一次指令。
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from astrbot.api.event import AstrMessageEvent, MessageEventResult

from ...registry import wf
from ..init import init_ready
from ..service import whisper as whisper_service
from ..util.command_args import command_args
from ..util.whisper_buttons import WHISPER_BUTTON_PREFIX


@wf.command("w", alias=["私聊", "whisper"])
async def wf_whisper(self, event: AstrMessageEvent):
    """获取市场卡片的私聊语句（可直接粘贴到游戏内）。"""
    await init_ready()

    raw = command_args(event, "w", "私聊", "whisper")
    session = event.unified_msg_origin
    sender = str(event.get_sender_id() or "")
    yield event.plain_result(whisper_service.reply_for(session, sender, raw))


@wf.button_action()
async def wf_whisper_button(
    self, event: AstrMessageEvent
) -> AsyncGenerator[MessageEventResult, None]:
    """市场卡片序号按钮 → 回复私聊语句 / Whisper pick button → reply text.

    与 ``/w 序号`` 完全等价（同一份 2 分钟缓存），只是免打字。仅接管
    id 前缀为 ``nyxbot:w:`` 的按钮，其余按钮不归这里管。
    """
    interaction = event.get_button_interaction()
    if interaction is None:
        return

    action_id = interaction.action_id or ""
    if not action_id.startswith(WHISPER_BUTTON_PREFIX):
        return  # 不是市场取句按钮，不接管

    # 行号优先取回调数据，缺失时从按钮 id 里恢复；结果指纹用于识别
    # 旧卡片的按钮（缓存已被新查询覆盖时提示重新查询）
    index = action_id.removeprefix(WHISPER_BUTTON_PREFIX).strip()
    data = interaction.data
    token: str | None = None
    if isinstance(data, dict):
        if isinstance(data.get("n"), str):
            index = data["n"].strip() or index
        if isinstance(data.get("k"), str):
            token = data["k"] or None

    session = event.unified_msg_origin
    sender = str(event.get_sender_id() or "")
    yield event.plain_result(whisper_service.reply_for(session, sender, index, token))
