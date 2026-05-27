"""虚空商人 Markdown 文本格式化器 / Void Trader Markdown Text Formatter

对应 card_void_trader.py 的图片渲染，在 QQ 官方平台替代图片卡片。
"""
from __future__ import annotations

from ..model.world_state.void_trader import VoidTrader


def _clean_item_name(item: str) -> str:
    """清理路径格式的物品名称 / Clean path-format item name."""
    return item.split("/")[-1].replace("_", " ")


def _format_credits(price: int) -> str:
    """格式化星币价格 / Format credits price."""
    if price >= 1000:
        return f"{price / 1000:.0f}K"
    return str(price)


def format_void_trader_markdown(trader: VoidTrader) -> str:
    """将虚空商人数据格式化为 Markdown 文本 / Format void trader as Markdown text."""
    trader_name = trader.character or "Baro'Ki Teel"
    location = trader.node or "未知位置"
    time_left = trader.time_left or "未知"

    lines: list[str] = [
        f"# 虚空商人 - {trader_name}",
        "",
        f"**位置**: {location}",
        f"**剩余时间**: {time_left}",
    ]

    if trader.manifest:
        lines.extend([
            "",
            "| 物品名称 | 杜卡币价格 | 星币价格 |",
            "|----------|------------|----------|",
        ])
        for item in trader.manifest:
            name = _clean_item_name(item.item) if item.item else "未知物品"
            ducats = str(item.prime_price) if item.prime_price is not None else "-"
            credits = _format_credits(item.regular_price) if item.regular_price else "0"
            lines.append(f"| {name} | {ducats} | {credits} |")

    lines.append("")
    lines.append("---")
    return "\n".join(lines)
