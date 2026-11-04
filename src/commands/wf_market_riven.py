"""wf_market_riven - Market 紫卡拍卖指令

指令:
  /WR  or  /wr  → 查询 Warframe.Market 紫卡拍卖

用法:
  /WR 武器名                              # 基础查询
  /WR 武器名 暴击率,暴击伤害                # 多参数：正面词条
  /WR 武器名 暴击率,暴击伤害 无              # 多参数：正面 + 负面词条
  /WR 武器名-暴击率,暴击伤害                # Java 风格：以 `-` 分隔
  /WR 武器名-暴击率,暴击伤害-无              # Java 风格：正面 + 负面词条
"""
from __future__ import annotations

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..init import init_ready
from ..render.card_market_orders import render_market_orders_possible_items_card
from ..render.card_market_riven import render_market_riven_card
from ..render.card_renderer import CardRenderer
from ..service.market_riven import MarketRivenService
from ..service.smart_match import remember_candidates, resolve_selection
from ..util.command_args import command_args, normalize_whitespace


def _split_riven_args(text: str) -> tuple[str, str, str]:
    """把 /WR 的原始参数拆成 (武器名, 正面词条, 负面词条)。

    与 service 层支持的两种写法保持一致：
      - 空格分参: ``Braton Prime 暴击率,暴击伤害 无``（武器名可含空格）
      - Java 风格: ``Braton Prime-暴击率,暴击伤害-无``（整段交给 service 按 ``-`` 拆）

    识别规则（从末尾往前找词条，遇到武器名即停）：
      - ``有`` / ``无`` → 负面词条限定
      - 含逗号且不含 ``-`` → 正面词条（含 ``-`` 的是 Java 风格整段，留给 service）

    Args:
        text: 指令之后的完整文本。

    Returns:
        (武器名, 正面词条, 负面词条)，缺失项为空字符串。
    """
    normalized = normalize_whitespace(text)
    tokens = normalized.split(" ") if normalized else []
    if not tokens:
        return "", "", ""

    positive_stats = ""
    negative_stats = ""
    index = len(tokens) - 1
    while index >= 1:
        token = tokens[index]
        if not negative_stats and token in {"有", "无"}:
            negative_stats = token
        elif (
            not positive_stats
            and "-" not in token
            and ("," in token or "，" in token)
        ):
            positive_stats = token
        else:
            break
        index -= 1

    return " ".join(tokens[: index + 1]), positive_stats, negative_stats


@wf.command("WR", alias=["wr"])
async def wf_market_riven(self, event: AstrMessageEvent):
    """查询 Warframe.Market 紫卡拍卖。

    武器名可以含空格（如 ``Braton Prime``），所以参数取整段原文后自行拆分，
    不能依赖框架按空格绑定的形参。
    """
    await init_ready()

    raw = command_args(event, "WR", "wr")

    # 上一次出了候选 → 允许用编号回选（保留后面的词条参数）
    session = event.unified_msg_origin
    selected = resolve_selection(session, raw)
    if selected:
        raw = selected

    if not raw:
        yield event.plain_result(
            """\
            请输入武器名称！用法：
            /WR 武器名
            /WR 武器名 暴击率,暴击伤害 无
            /WR 武器名-暴击率,暴击伤害-无\
            """,
        )
        return

    keyword, positive_stats, negative_stats = _split_riven_args(raw)
    if not keyword:
        yield event.plain_result("请输入武器名称！")
        return

    try:
        result = await MarketRivenService.search_market_riven(
            keyword.strip(),
            positive_stats=positive_stats.strip(),
            negative_stats=negative_stats.strip(),
        )
    except Exception:
        logger.exception("查询紫卡拍卖失败")
        yield event.plain_result("查询紫卡拍卖失败，请检查名称是否正确或稍后重试")
        return

    if isinstance(result, tuple):
        candidates, _ = result
        if not candidates:
            yield event.plain_result(f"未找到匹配的紫卡武器: {keyword}")
            return
        candidates = candidates[:15]
        remember_candidates(session, candidates)
        chain = await CardRenderer.render_card_to_chain_result(
            render_market_orders_possible_items_card,
            candidates,
            hint=f"回复 /WR 1~{len(candidates)} 查询（60 秒内有效）",
        )
        yield event.chain_result(chain)
        return

    if result is None:
        yield event.plain_result(f"未找到匹配的紫卡武器: {keyword}")
        return

    chain = await CardRenderer.render_card_to_chain_result(
        render_market_riven_card, result
    )
    yield event.chain_result(chain)
