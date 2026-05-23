"""
Faction Enum / 派系枚举
包含星际战甲中所有派系的中英文名称、代表颜色及图标。

重构为 StrEnum：value 即为成员名称字符串（与 Java enum 行为一致）。
mode="json" 序列化输出 "FC_GRINEER" 而非 ["Grineer", "#870507", "\ue401"]，
Pydantic 反序列化直接用字符串匹配，无需 _missing_ 钩子。
"""
from __future__ import annotations

from enum import StrEnum


class FactionEnum(StrEnum):
    """派系枚举 — value = 成员名称字符串"""

    FC_GRINEER = ("FC_GRINEER", "Grineer", "#870507", "\ue401")
    FC_CORPUS = ("FC_CORPUS", "Corpus", "#5AB0CB", "\ue402")
    FC_INFESTATION = ("FC_INFESTATION", "Infested", "#61814B", "\ue403")
    FC_OROKIN = ("FC_OROKIN", "奥罗金", "#B6A019", "\ue404")
    FC_CORRUPTED = ("FC_CORRUPTED", "堕落者", "#B6A019", "\ue404")
    FC_SENTIENT = ("FC_SENTIENT", "Sentient", "#931B1B", "\ue405")
    FC_NARMER = ("FC_NARMER", "合一众", "#A35F27", "\ue409")
    FC_MURMUR = ("FC_MURMUR", "低语者", "#B59B6D", "\ue410")
    FC_SCALDRA = ("FC_SCALDRA", "炽蛇军", "#DC8E12", "\ue411")
    FC_TECHROT = ("FC_TECHROT", "科腐者", "#17A36A", "\ue412")
    FC_DUVIRI = ("FC_DUVIRI", "双衍王境", "#000000", "")
    FC_MITW = ("FC_MITW", "墙中人", "#000000", "")
    FC_TENNO = ("FC_TENNO", "TENNO", "#000000", "\ue400")
    FC_CROSSFIRE = ("FC_CROSSFIRE", "多方交战", "#591A9C", "\ue413")
    FC_NONE = ("FC_NONE", "未知派系", "#000000", "")

    def __new__(cls, value: str, display_name: str, color: str, icon: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj._display_name = display_name # pyright: ignore[reportAttributeAccessIssue]
        obj._color = color # pyright: ignore[reportAttributeAccessIssue]
        obj._icon = icon # pyright: ignore[reportAttributeAccessIssue]
        return obj

    @property
    def display_name(self) -> str:
        """派系显示名称"""
        return self._display_name # type: ignore

    @property
    def color(self) -> str:
        """派系代表颜色（十六进制）"""
        return self._color # type: ignore

    @property
    def icon(self) -> str:
        """派系图标（Unicode 字符）"""
        return self._icon # type: ignore
