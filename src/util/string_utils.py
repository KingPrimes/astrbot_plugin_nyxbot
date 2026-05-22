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


def split_camel_case(text: str) -> str:
    """将驼峰命名拆分为空格分隔的单词并转为 Title Case。

    镜像 Java StringUtils.splitCamelCase() + WordUtils.capitalizeFully()。

    示例::
        "KarakBlueprint"   → "Karak Blueprint"
        "VoltPrimeHelmet"  → "Volt Prime Helmet"
        "VeloxPrimeBarrel" → "Velox Prime Barrel"

    Args:
        text: 驼峰命名的字符串。

    Returns:
        拆分并规范化后的字符串；空字符串原样返回。
    """
    if not text:
        return text
    # 第一步：在非数字字符后的大写字母前插入空格
    processed = re.sub(r"(?<=\D)(?=[A-Z])", " ", text)
    # 第二步：每个单词首字母大写，其余小写（镜像 WordUtils.capitalizeFully）
    return processed.title()


def get_last_three_segments(path: str, sep: str = "/") -> str | None:
    """提取路径的最后 N 段（默认3段）。

    示例::
        "/Lotus/Weapons/Grineer/Karak/KarakBlueprint" → "Grineer/Karak/KarakBlueprint"
        "/Lotus/StoreItems/..." → "StoreItems/..."
        "A/B" → "A/B"  (少于3段时返回全部)

    Args:
        path: 分隔符分隔的路径字符串。
        sep: 分隔符，默认 "/"。

    Returns:
        最后3段组成的字符串，路径为空时返回 None。
    """
    if not path:
        return None
    parts = [p for p in path.split(sep) if p]
    if len(parts) <= 3:
        return sep.join(parts)
    return sep.join(parts[-3:])
