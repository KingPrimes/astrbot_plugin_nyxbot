"""i18n utilities / 国际化工具

提供从 Warframe Market API 返回数据中提取本地化信息的共享函数。
"""
from __future__ import annotations


def extract_i18n(item: dict, lang: str = "zh-hans") -> dict:
    """从 API 返回的 item 中提取 i18n 本地化 name/icon/thumb。

    所有 Market API 端点返回的 item 都遵循统一结构:
        item["i18n"][lang] = {"name": "...", "icon": "...", "thumb": "..."}

    Args:
        item: API 返回的原始 item 字典。
        lang: 目标语言代码，默认 "zh-hans"。

    Returns:
        包含 name/icon/thumb 的 dict，缺失时值为 None。
    """
    i18n = item.get("i18n", {})
    localized = i18n.get(lang, {})
    return {
        "name": localized.get("name"),
        "icon": localized.get("icon"),
        "thumb": localized.get("thumb"),
    }
