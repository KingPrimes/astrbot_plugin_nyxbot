"""/wf help - Show help information / 显示帮助信息"""

from __future__ import annotations

from astrbot.api.event import AstrMessageEvent

from ...registry import command_prefix, wf


@wf.command("wfhelp")
async def wf_help(self, event: AstrMessageEvent):
    """显示 Warframe 助手指令帮助"""
    prefix = f"/{command_prefix} " if command_prefix else "/"
    yield event.plain_result(
        f"""\
            ## NyxBot Warframe 助手

            | 指令 | 说明 |
            |------|------|
            | `{prefix}平原` | 查看平原周期 |
            | `{prefix}警报` | 查看当前警报 |
            | `{prefix}突击` | 查看每日突击 |
            | `{prefix}裂缝` | 查看虚空裂缝 |
            | `{prefix}奸商` | 查看虚空商人 |
            | `{prefix}钢铁` | 查看钢铁之路 |
            | `{prefix}仲裁` | 查看仲裁任务 |
            | `{prefix}1999` | 查看1999日历 |
            | `{prefix}WM` | 查询Warframe.Market订单 |
            | `{prefix}金垃圾` | 查看杜卡德金币 |
            | `{prefix}CD` | 查询赤毒巫妖拍卖 |
            | `{prefix}XT` | 查询信条姐妹拍卖 |
            | `{prefix}WR` | 查询紫卡拍卖 |
            | `{prefix}遗物` | 查询遗物数据 |
            | `{prefix}紫卡分析` | OCR识别紫卡 |
            | `{prefix}全周期` | 查看所有开放世界周期 |
            | `{prefix}wfhelp` | 显示本帮助 |\
            """,
    )
