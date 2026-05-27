"""突击 Markdown 文本格式化器 / Sortie Markdown Text Formatter

对应 card_sortie.py 的图片渲染，在 QQ 官方平台替代图片卡片。
"""
from __future__ import annotations

from ..model.world_state.sortie import Sortie


def _build_variant_rows(variants: list) -> str:
    lines: list[str] = []
    for i, v in enumerate(variants, 1):
        mt = v.mission_type.display_name if v.mission_type else "?"
        node = v.node or "未知节点"
        modifier = v.modifier_type.value if v.modifier_type else "-"
        lines.append(f"{i}. {node}")
        lines.append(f"    - {mt}")
        lines.append(f"    - {modifier}")
        lines.append("")
        if i < len(variants):
            lines.append("---")
            lines.append("")
    return "\n".join(lines)


def format_sorties_markdown(sortie: Sortie) -> str:
    """将突击数据格式化为 Markdown 文本 / Format sortie as Markdown text."""
    boss_name = sortie.boss.display_name if sortie.boss else "未知"

    lines: list[str] = [
        "# 突击任务",
        "",
        f"### **Boss**: {boss_name}",
        "",
        _build_variant_rows(sortie.variants),
        "---",
    ]

    return "\n".join(lines)
