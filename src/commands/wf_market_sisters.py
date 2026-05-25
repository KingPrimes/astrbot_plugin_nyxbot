"""wf_market_sisters - 信条姐妹拍卖指令

指令:
  /XT  or  /信条  or  /xt  → 查询 Market 信条姐妹拍卖
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from astrbot.api.event import AstrMessageEvent, MessageEventResult

from ...registry import wf
from .wf_market_liches import _handle_lich_sister


@wf.command("XT",alias=["xt","信条"])
async def wf_market_sisters(self, event: AstrMessageEvent, keyword: str = "") -> AsyncGenerator[MessageEventResult, None]:
    async for r in _handle_lich_sister(event, keyword, "sister", "信条"):
        yield r
