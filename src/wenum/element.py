"""
Element Enum / 元素枚举
包含星际战甲中所有伤害/元素类型的中文名称、代表颜色及图标。
使用 Warframe_Font_Icon 字体图标。

重构为 StrEnum：value 即为成员名称字符串（与 Java enum 行为一致）。
"""
from __future__ import annotations

from enum import StrEnum, unique


@unique
class ElementEnum(StrEnum):
    """元素枚举 — value = 成员名称字符串"""

    ELECTRICITY = ("ELECTRICITY", "电击", "#955ab9", "\ue601")
    IMPACT = ("IMPACT", "冲击", "#929595", "\ue602")
    RADIATION = ("RADIATION", "辐射", "#9E940C", "\ue603")
    MAGNETIC = ("MAGNETIC", "磁力", "#50575E", "\ue604")
    COLD = ("COLD", "冰冻", "#2C53B5", "\ue605")
    TOXIN = ("TOXIN", "毒素", "#4F822F", "\ue606")
    HEAT = ("HEAT", "火焰", "#E56E0C", "\ue607")
    PUNCTURE = ("PUNCTURE", "穿刺", "#8D8676", "\ue608")
    SLASH = ("SLASH", "切割", "#876769", "\ue609")
    BLAST = ("BLAST", "爆炸", "#A86668", "\ue610")
    CORROSIVE = ("CORROSIVE", "腐蚀", "#B2CA01", "\ue611")
    GAS = ("GAS", "毒气", "#3AC490", "\ue612")
    VIRAL = ("VIRAL", "病毒", "#E374B6", "\ue613")
    VOID = ("VOID", "虚空", "#016468", "\ue614")
    TAU = ("TAU", "TAU", "#DF191E", "\ue615")
    TRUE = ("TRUE", "TRUE", "#66582E", "\ue616")

    def __new__(cls, value: str, display_name: str, color: str, icon: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj._display_name = display_name  # type: ignore
        obj._color = color  # type: ignore
        obj._icon = icon  # type: ignore
        return obj

    @property
    def display_name(self) -> str:
        """元素中文名称"""
        return self._display_name  # type: ignore

    @property
    def color(self) -> str:
        """元素代表颜色（十六进制字符串）"""
        return self._color  # type: ignore

    @property
    def icon(self) -> str:
        """元素图标（Unicode 字符，Warframe_Font_Icon 字体）"""
        return self._icon  # type: ignore
