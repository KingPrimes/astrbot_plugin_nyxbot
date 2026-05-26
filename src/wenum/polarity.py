"""
Polarity Enum / Mod 极性槽位枚举
使用 Warframe_Font_Icon 字体图标表示各极性符号。
"""
from __future__ import annotations

from enum import StrEnum, unique


@unique
class PolarityEnum(StrEnum):
    """Mod 极性槽位枚举 — value = 成员名称字符串"""

    MADURAI = ("MADURAI", "\ue200")
    VAZARIN = ("VAZARIN", "\ue202")
    NARAMON = ("NARAMON", "\ue203")
    ZENURIK = ("ZENURIK", "\ue204")
    UNAIRU = ("UNAIRU", "\ue205")
    PENJAGA = ("PENJAGA", "\ue206")
    UMBRA = ("UMBRA", "\ue207")
    ANY = ("ANY", "\ue208")

    def __new__(cls, value: str, icon: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj._icon = icon  # type: ignore
        return obj

    @property
    def icon(self) -> str:
        """极性图标 Unicode 字符（Warframe_Font_Icon 字体）"""
        return self._icon  # type: ignore
