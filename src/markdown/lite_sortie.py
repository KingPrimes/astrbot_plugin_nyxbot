"""执刑官猎杀 Markdown 文本格式化器 / Lite Sortie Markdown Text Formatter

对应 card_lite_sortie.py 的图片渲染，在 QQ 官方平台替代图片卡片。
"""
from __future__ import annotations

from datetime import datetime, timezone

from ..model.world_state.lite_sortie import LiteSortie


def _format_expiry(expiry) -> str:
    """将 DateField 的毫秒时间戳格式化为 YYYY-MM-DD HH:MM:SS"""
    if expiry is None:
        return "未知"
    return datetime.fromtimestamp(
        expiry.time_millis / 1000, tz=timezone.utc
    ).strftime("%Y-%m-%d %H:%M:%S")


def format_lite_sorties_markdown(lite_sortie: LiteSortie) -> str:
    """将执刑官猎杀数据格式化为 Markdown 文本 / Format lite sortie as Markdown text."""
    boss_name = lite_sortie.boss.display_name if lite_sortie.boss else "未知"
    end_time = _format_expiry(lite_sortie.expiry)

    lines: list[str] = [
        "# 执刑官猎杀",
        "",
        f"**Boss**: {boss_name}",
        f"**结束时间**: {end_time}",
        "",
        "## 任务列表",
    ]

    for m in lite_sortie.missions:
        mt = m.mission_type.display_name if m.mission_type else "?"
        node = m.node or "未知节点"
        lines.append(f"- {mt} - {node}")

    lines.append("")
    lines.append("---")
    return "\n".join(lines)
