"""/wf help - Show help information / 显示帮助信息"""

from __future__ import annotations

from astrbot.api.event import AstrMessageEvent

from ...registry import command_prefix, wf


@wf.command("wfhelp")
async def wf_help(self, event: AstrMessageEvent):
    """显示 Warframe 助手指令帮助"""
    prefix = f"/{command_prefix} " if command_prefix else "/"
    yield event.plain_result(
        "NyxBot Warframe 助手 — 可用指令：\n\n"
        f"  {prefix}平原     查看平原周期\n"
        f"  {prefix}警报     查看当前警报\n"
        f"  {prefix}突击     查看每日突击\n"
        f"  {prefix}裂缝     查看虚空裂缝\n"
        f"  {prefix}奸商     查看虚空商人\n"
        f"  {prefix}钢铁     查看钢铁之路\n"
        f"  {prefix}仲裁     查看仲裁任务\n"
        f"  {prefix}1999     查看1999日历\n"
        f"  {prefix}WM       查询Warframe.Market订单\n"
        f"  {prefix}金垃圾   查看杜卡德金币\n"
        f"  {prefix}CD       查询赤毒巫妖拍卖\n"
        f"  {prefix}XT       查询信条姐妹拍卖\n"
        f"  {prefix}WR       查询紫卡拍卖\n"
        f"  {prefix}遗物     查询遗物数据\n"
        f"  {prefix}紫卡分析 OCR识别紫卡\n"
        f"  {prefix}全周期   查看所有开放世界周期\n"
        f"  {prefix}wfhelp   显示本帮助"
    )
