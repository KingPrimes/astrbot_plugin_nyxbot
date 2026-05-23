"""
Message Model / 消息模型

对应 Java: Message.java
不继承 BastWorldState，包含 LanguageCode（枚举）和 Message（本地化字符串路径）。
用于 Event.messages。
"""
from __future__ import annotations

from enum import Enum

from pydantic import Field

from .base import BaseModelWithAlias


class LanguageCode(Enum):
    """语言代码枚举 / Language Code Enum

    对应 Java: Message.LanguageCode
    """
    en = "en"
    zh = "zh"
    ko = "ko"
    ru = "ru"
    tr = "tr"
    es = "es"
    fr = "fr"
    de = "de"
    it = "it"
    jp = "jp"
    pl = "pl"
    pt = "pt"
    vi = "vi"
    id = "id"
    th = "th"
    ar = "ar"
    fa = "fa"
    he = "he"
    hy = "hy"
    ka = "ka"
    kr = "kr"
    ms = "ms"
    no = "no"
    sq = "sq"
    sw = "sw"
    tl = "tl"
    uk = "uk"
    uz = "uz"
    zh_tw = "zh_tw"
    tc = "tc"
    ja = "ja"


class Message(BaseModelWithAlias):
    """消息 / Message

    对应 Java: Message
    """

    language_code: LanguageCode | None = Field(default=None, alias="LanguageCode")
    message: str | None = Field(default=None, alias="Message")

