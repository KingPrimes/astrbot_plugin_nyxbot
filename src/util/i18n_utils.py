"""i18n utilities / 国际化工具

提供从 Warframe Market API 返回数据中提取本地化信息的共享函数。
"""
from __future__ import annotations

#: ``extract_i18n`` 会产出的键（与各表的列名一致）
I18N_FIELDS = (
    "name",
    "enName",
    "icon",
    "thumb",
    "subIcon",
    "description",
    "wikiLink",
)


def extract_i18n(item: dict, lang: str = "zh-hans") -> dict:
    """从 API 返回的 item 中提取本地化字段。

    结构（见 data-models 文档）::

        item["i18n"][lang] = {
            "name": "...", "icon": "...", "thumb": "...",
            "subIcon": "...", "description": "...", "wikiLink": "..."
        }

    除目标语言外，始终附带英文名 ``enName``（私聊语句与英文搜索要用）。

    Args:
        item: API 返回的原始 item 字典。
        lang: 目标语言代码，默认 ``zh-hans``。

    Returns:
        扁平 dict，只包含**非 None** 的键，便于 ``{**item, **extract_i18n(item)}``
        之后配合「缺失字段不更新」的 upsert 逻辑。
    """
    i18n = item.get("i18n") or {}
    localized = i18n.get(lang) or {}
    english = i18n.get("en") or {}

    raw = {
        "name": localized.get("name"),
        "enName": english.get("name"),
        "icon": localized.get("icon"),
        "thumb": localized.get("thumb"),
        "subIcon": localized.get("subIcon"),
        "description": localized.get("description"),
        "wikiLink": localized.get("wikiLink"),
    }
    return {key: value for key, value in raw.items() if value is not None}
