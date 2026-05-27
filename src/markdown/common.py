"""Markdown 公共工具 / Markdown Common Utilities

供 src/markdown/ 下的各格式化器使用的共享函数。
"""
from __future__ import annotations

_DEFAULT_FOOTER_AUTHOR = "KingPrimes"


def markdown_footer(author: str | None = None) -> str:
    """生成 Markdown 底部署名 / Generate Markdown footer signature."""
    name = author or _DEFAULT_FOOTER_AUTHOR
    return f"\n\n---\nPosted by: {name}"
