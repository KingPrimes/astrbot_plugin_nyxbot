"""wf_market_orders - Market 市场订单查询指令

指令:
  /WM  or  /市场  or  /wm  or  /market  → 查询 Warframe.Market 物品订单

支持参数（可写在物品名前后）:
  满级 | MAX  → 仅查询满级物品
  购买 | 买家 | BUY   → 查询买家报价
  出售 | 卖家 | SELL  → 查询卖家报价
  PC | PS4 | XBOX | SWITCH  → 指定平台

物品名可以含空格（如 ``Frost Prime Set``），因此参数不能交给框架按空格
绑定形参，改为读原始文本后自己解析（见 ``util.command_args``）。
"""
from __future__ import annotations

import re

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..init import init_ready
from ..render.card_market_orders import (
    render_market_orders_card,
    render_market_orders_possible_items_card,
)
from ..render.card_renderer import CardRenderer
from ..service.market_orders import MarketOrdersService
from ..service.smart_match import remember_candidates, resolve_selection
from ..util.command_args import command_args, normalize_whitespace

# 平台关键字 → 内部平台标识（对齐 Go marketPlatformKeywords，按长度降序，
# 避免 "PC" 抢先命中 "SWITCH" 之类的前缀）
_PLATFORM_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("SWITCH", "switch"),
    ("MOBILE", "mobile"),
    ("XBOX", "xbox"),
    ("PS4", "ps4"),
    ("PC", "pc"),
)

# 满级 / 买卖方向关键字（对齐 Go marketMaxKeywords / marketBuyerKeywords）
_MAX_KEYWORDS = ("满级", "MAX", "max")
_BUY_KEYWORDS = ("购买", "买家", "BUY", "buy")
_SELL_KEYWORDS = ("出售", "卖家", "SELL", "sell")


def _strip_first_keyword(text: str, keywords: tuple[str, ...]) -> tuple[bool, str]:
    """去掉首个命中的关键字（连同其全部出现），对齐 Go ``stripFirstMatch``。

    区分大小写：Go 用 ``strings.Contains`` 逐个关键字匹配，所以 ``Maxim``
    这类名字不会被 ``MAX``/``max`` 误伤。此处保持同样语义，避免把物品名
    中的 ``Max`` 当成满级标志。
    """
    for keyword in keywords:
        if keyword in text:
            return True, text.replace(keyword, "")
    return False, text


def _parse_params(text: str) -> tuple[str, str, bool, bool]:
    """解析订单查询参数。

    Args:
        text: 指令之后的完整文本（未切分），如 ``Frost Prime Set 满级 PC``。

    Returns:
        (keyword, platform, is_by, is_max)
    """
    platform = "pc"
    is_by = False  # False=出售(SELL), True=购买(BUY)
    processed = text

    # 平台：大小写不敏感（对齐 Go removeAllFold）
    for keyword, value in _PLATFORM_KEYWORDS:
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        if pattern.search(processed):
            platform = value
            processed = pattern.sub("", processed)
            break

    # 满级
    is_max, processed = _strip_first_keyword(processed, _MAX_KEYWORDS)

    # 买卖方向：购买优先，出售是默认方向
    matched, processed = _strip_first_keyword(processed, _BUY_KEYWORDS)
    if matched:
        is_by = True
    else:
        _, processed = _strip_first_keyword(processed, _SELL_KEYWORDS)

    return normalize_whitespace(processed), platform, is_by, is_max


@wf.command(name="WM", alias=["市场", "wm", "market"])
async def wf_market_orders(self, event: AstrMessageEvent):
    """查询 Warframe.Market 物品订单"""
    await init_ready()

    # 物品名可能含空格，取整段原文（框架按空格切参会把它截断）
    raw = command_args(event, "WM", "市场", "wm", "market")

    # 上一次出了候选 → 允许用编号回选
    session = event.unified_msg_origin
    selected = resolve_selection(session, raw, "WM")
    if selected:
        raw = selected

    if not raw:
        yield event.plain_result("请输入正确的名称！用法：/WM 物品名称 [满级|MAX] [购买|出售] [PC|PS4|XBOX|SWITCH]")
        return

    keyword, platform, is_by, is_max = _parse_params(raw)
    if not keyword:
        yield event.plain_result("请输入正确的名称！")
        return

    try:
        result = await MarketOrdersService.search_market_orders(
            keyword, platform, is_by, is_max
        )
    except Exception:
        logger.exception("查询市场订单失败")
        yield event.plain_result("查询市场订单失败，请检查名称是否正确或稍后重试")
        return

    if result.possible_items:
        possible_items = result.possible_items[:15]
        remember_candidates(session, possible_items, "WM")
        chain = await CardRenderer.render_card_to_chain_result(
            render_market_orders_possible_items_card,
            possible_items,
            hint=f"回复 /WM 1~{len(possible_items)} 查询（60 秒内有效）",
        )
        yield event.chain_result(chain)
        return

    if result.result is None:
        yield event.plain_result(f"未找到匹配的物品: {keyword}")
        return

    chain = await CardRenderer.render_card_to_chain_result(
        render_market_orders_card, result.result
    )
    yield event.chain_result(chain)
