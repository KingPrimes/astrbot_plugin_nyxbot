"""警报 Markdown 文本格式化器 / Alert Markdown Text Formatter

对应 card_alert.py 的图片渲染，在 QQ 官方平台替代图片卡片。
Each alert rendered as a compact block: bold header + blockquote with details.
"""
from __future__ import annotations

from ..model.world_state import Alert


def _build_reward_text(alert: Alert) -> str:
    mi = alert.mission_info
    if mi is None:
        return ""
    reward = mi.mission_reward
    if reward is None:
        return ""

    segments: list[str] = []

    if reward.credits and reward.credits > 0:
        segments.append(f"{reward.credits} 星币")

    if reward.counted_items:
        item_texts: list[str] = []
        for item in reward.counted_items[:5]:
            name = item.name.split("/")[-1] if "/" in item.name else item.name
            item_texts.append(f"{name}×{item.count}" if item.count > 1 else name)
        segments.append("  ".join(item_texts))

    return "  ".join(segments)


def format_alerts_markdown(alerts: list[Alert]) -> str:
    """将警报列表格式化为 Markdown 文本 / Format alerts as Markdown text.

    Each alert gets a bold header with node name and a blockquote
    containing mission type, faction, level range, reward, and time left.
    """
    lines: list[str] = [f"# 警报（共 {len(alerts)} 个）", ""]

    for i, alert in enumerate(alerts, 1):
        mi = alert.mission_info
        location = mi.location if mi and mi.location else "未知节点"
        location_short = location.split("/")[-1] if "/" in location else location

        lines.append(f"**{i}. {location_short}**")

        detail_parts: list[str] = []

        if mi and mi.mission_type:
            detail_parts.append(mi.mission_type.display_name)

        if mi and mi.faction:
            detail_parts.append(mi.faction.display_name)

        if mi and (mi.min_enemy_level or mi.max_enemy_level):
            lo = mi.min_enemy_level or "?"
            hi = mi.max_enemy_level or "?"
            detail_parts.append(f"Lv{lo}–{hi}")

        detail_parts.append(f"剩余 {alert.time_left}")

        lines.append(f"- {' | '.join(detail_parts)}")

        reward_text = _build_reward_text(alert)
        if reward_text:
            lines.append(f"- **{reward_text}**")

        lines.append("")

        if i < len(alerts):
            lines.append("---")
            lines.append("")

    return "\n".join(lines)
