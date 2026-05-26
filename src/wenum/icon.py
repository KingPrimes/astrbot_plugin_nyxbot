"""
Icon Enum / 图标枚举
使用 Warframe_Font_Icon 字体图标，提供通用图标字符映射。
"""
from __future__ import annotations

from enum import StrEnum, unique


@unique
class IconEnum(StrEnum):
    """图标枚举 — value = 成员名称字符串"""

    SMILE = ("SMILE", "\ue300")
    MEH = ("MEH", "\ue302")
    CUBES = ("CUBES", "\ue304")
    DUCATS = ("DUCATS", "\ue305")
    CREDITS = ("CREDITS", "\ue306")
    AYAN = ("AYAN", "\ue308")
    PLATINUM = ("PLATINUM", "\ue309")
    REFRESH = ("REFRESH", "\ue310")
    COLD = ("COLD", "\ue100")
    SUN = ("SUN", "\ue101")
    NIGHT = ("NIGHT", "\ue102")

    def __new__(cls, value: str, icon: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj._icon = icon  # type: ignore
        return obj

    @property
    def icon(self) -> str:
        """图标 Unicode 字符（Warframe_Font_Icon 字体）"""
        return self._icon  # type: ignore
