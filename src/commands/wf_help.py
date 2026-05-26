"""/wf help - Show help information / 显示帮助信息"""

from __future__ import annotations

from astrbot.api.event import AstrMessageEvent

from ...registry import command_prefix, wf


@wf.command("wfhelp")
async def wf_help(self, event: AstrMessageEvent):
    """显示 Warframe 助手指令帮助"""
    yield event.plain_result(
            f"你好！我是 NyxBot Warframe 助手，输入 {command_prefix} wfhelp 查看所有可用指令。"
        )
