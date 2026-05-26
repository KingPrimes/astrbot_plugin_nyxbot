"""
Riven Trend Enum / 紫卡倾向枚举
紫卡倾向用圆点 (●○○○○) 表示，范围为 0.5 ~ 1.55（共五档）。
"""
from __future__ import annotations

from enum import StrEnum, unique


@unique
class RivenTrendEnum(StrEnum):
    """紫卡倾向枚举 — value = 成员名称字符串"""

    RIVEN_TREND_1 = ("RIVEN_TREND_1", "●○○○○")
    RIVEN_TREND_2 = ("RIVEN_TREND_2", "●●○○○")
    RIVEN_TREND_3 = ("RIVEN_TREND_3", "●●●○○")
    RIVEN_TREND_4 = ("RIVEN_TREND_4", "●●●●○")
    RIVEN_TREND_5 = ("RIVEN_TREND_5", "●●●●●")

    def __new__(cls, value: str, doc: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj._doc = doc  # type: ignore
        return obj

    @property
    def doc(self) -> str:
        """倾向点数圆点表示（如 '●●●○○'）"""
        return self._doc  # type: ignore

    @classmethod
    def get_riven_trend_dot(cls, dot: float) -> str | None:
        """根据倾向数值获取对应的圆点表示

        Args:
            dot: 紫卡倾向数值 (0.5 ~ 1.55)

        Returns:
            对应档位的圆点字符串，如 '●●●○○'
        """
        if dot < 0.7:
            return cls.RIVEN_TREND_1.doc
        if dot < 0.9:
            return cls.RIVEN_TREND_2.doc
        if dot < 1.15:
            return cls.RIVEN_TREND_3.doc
        if dot < 1.3:
            return cls.RIVEN_TREND_4.doc
        return cls.RIVEN_TREND_5.doc
