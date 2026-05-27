"""每日特惠 Markdown 文本格式化器 / Daily Deals Markdown Text Formatter

对应 card_daily_deals.py 的图片渲染，在 QQ 官方平台替代图片卡片。
"""
from __future__ import annotations

from ..model.world_state.daily_deals import DailyDeals


def _clean_item_name(item: str) -> str:
    """清理路径格式的物品名称 / Clean path-format item name."""
    return item.split("/")[-1] if "/" in item else item


def _format_discount(discount: float) -> str:
    """格式化折扣比 / Format discount percentage."""
    pct = round(discount * 100) if discount < 1 else round(discount)
    return f"{pct}%"


def format_daily_deals_markdown(deals: list[DailyDeals]) -> str:
    """将每日特惠数据格式化为 Markdown 文本 / Format daily deals as Markdown text."""
    if not deals:
        return "当前没有每日特惠数据"

    d = deals[0]
    item_name = _clean_item_name(d.item) if d.item else "未知物品"
    original = d.original_price or 0
    sale = d.sale_price or 0
    discount = _format_discount(d.discount) if d.discount is not None else "?"
    sold = d.sold or 0
    total = d.total or 0
    time_left = d.time_left or "未知"

    lines: list[str] = [
        "# 每日特惠",
        f"- 物品名称  ->  **{item_name}**",
        f"- 原价/现价  -> ~~{original}~~ / {sale}",
        f"- 折扣比    ->  {discount}",
        f"- 总/余     ->  {total} / {sold}",
        f"- 剩余时间   ->  {time_left}",
    ]

    return "\n".join(lines)
