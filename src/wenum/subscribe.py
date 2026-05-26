"""Subscribe Enums / 订阅类型枚举"""
from __future__ import annotations

from enum import StrEnum, unique


@unique
class SubscribeEnums(StrEnum):
    """订阅类型枚举 — value = 成员名称字符串"""

    ALERTS = ("ALERTS", "警报", "alerts")
    INVASIONS = ("INVASIONS", "入侵", "invasions")
    FISSURES = ("FISSURES", "裂隙", "fissures")
    SORTIE = ("SORTIE", "突击", "sortie")
    ARBITRATION = ("ARBITRATION", "仲裁", "arbitration")
    VOID = ("VOID", "虚空", "void")
    NIGHTWAVE = ("NIGHTWAVE", "电波", "nightwave")
    STEEL_PATH = ("STEEL_PATH", "钢铁之路", "steel_path")
    DUVIRI = ("DUVIRI", "双衍王境", "duviri")
    CYCLE = ("CYCLE", "轮换", "cycle")

    def __new__(cls, value: str, cn_name: str, en_name: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj._cn_name = cn_name  # type: ignore
        obj._en_name = en_name  # type: ignore
        return obj

    @property
    def cn_name(self) -> str:
        """中文名称"""
        return self._cn_name  # type: ignore

    @property
    def en_name(self) -> str:
        """英文名称"""
        return self._en_name  # type: ignore

    @classmethod
    def from_en_name(cls, en_name: str) -> SubscribeEnums:
        """根据英文名称获取枚举成员"""
        mapping = {m.en_name: m for m in cls}
        return mapping.get(en_name.lower(), cls.ALERTS)
