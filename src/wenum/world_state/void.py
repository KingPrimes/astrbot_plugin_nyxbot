"""
Void Enum / 虚空遗物等级枚举
包含星际战甲中虚空遗物的 6 个等级名称及代表颜色。

重构为 StrEnum：value 即为成员名称字符串（与 Java enum 行为一致）。
mode="json" 序列化输出 "VoidT4" 而非 ["后纪", "#C1BE39"]。
"""
from __future__ import annotations

from enum import StrEnum


class VoidEnum(StrEnum):
    """虚空遗物等级枚举 — value = 成员名称字符串"""

    VoidT1 = ("VoidT1", "古纪", "#514234")
    VoidT2 = ("VoidT2", "前纪", "#75562B")
    VoidT3 = ("VoidT3", "中纪", "#9F9E9E")
    VoidT4 = ("VoidT4", "后纪", "#C1BE39")
    VoidT5 = ("VoidT5", "安魂", "#872A2C")
    VoidT6 = ("VoidT6", "全能", "#7F8C8D")

    def __new__(cls, value: str, display_name: str, color: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj._display_name = display_name # type: ignore
        obj._color = color # type: ignore
        return obj

    @property
    def display_name(self) -> str:
        """遗物等级显示名称"""
        return self._display_name # type: ignore

    @property
    def color(self) -> str:
        """遗物等级代表颜色（十六进制字符串）"""
        return self._color # type: ignore
