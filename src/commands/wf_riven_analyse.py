"""wf_riven_analyse - 紫卡分析指令

指令:
  /紫卡分析  or  /分析紫卡  → OCR 识别紫卡图片并进行属性趋势分析

注意: 需要 OCR 能力，当前 Python 环境下暂不完整实现。
"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent

from ...registry import wf


@wf.command(name="紫卡分析", alias=["分析紫卡"])
async def wf_riven_analyse(self, event: AstrMessageEvent):
    """OCR 识别紫卡图片并进行属性趋势分析"""
    yield event.plain_result(
        "紫卡分析功能需要 OCR 支持，当前版本暂不完整实现。\n"
        "请使用 /WR 武器名称 查询紫卡市场数据。"
    )
