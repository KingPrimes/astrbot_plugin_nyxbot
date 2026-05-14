"""String utilities / 字符串工具函数"""
from __future__ import annotations

import re


def to_title_case(text: str) -> str:
    """将分隔命名转换为每个部分首字母大写，保留原分隔符。

    示例::
        "HELLO WORLD"       → "Hello World"        （空格分隔）
        "hello_world"       → "Hello_World"         （下划线分隔）
        "mk1-braton"        → "Mk1-Braton"          （连字符分隔）
        "braton-vandal"     → "Braton-Vandal"
        "MK1-BRATON"        → "Mk1-Braton"
        "hello world"       → "Hello World"
        "HELLO & WORLD"     → "Hello & World"       （& 符号保留）
        "braton&vandal"     → "Braton&Vandal"
        "braton & vandal"   → "Braton & Vandal"

    Args:
        text: 输入字符串。

    Returns:
        转换后的字符串。
    """
    if not text:
        return ""
    # 用正则分割，保留分隔符和特殊符号
    # 匹配：字母数字连续块 或 分隔符/符号
    parts = re.split(r"([^a-zA-Z0-9]+)", text)
    result_parts: list[str] = []
    for p in parts:
        if not p:
            continue
        # 如果是分隔符/符号（非字母数字），原样保留
        if re.search(r"[^a-zA-Z0-9]", p):
            result_parts.append(p)
        else:
            # 字母数字块：首字母大写
            result_parts.append(p.capitalize())
    return "".join(result_parts)
