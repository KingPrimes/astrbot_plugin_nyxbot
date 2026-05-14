"""Subscribe Enums / 订阅类型枚举"""
from __future__ import annotations

from enum import Enum


class SubscribeEnums(Enum):
    """订阅类型枚举"""

    ALERTS = ("警报", "alerts")
    INVASIONS = ("入侵", "invasions")
    FISSURES = ("裂隙", "fissures")
    SORTIE = ("突击", "sortie")
    ARBITRATION = ("仲裁", "arbitration")
    VOID = ("虚空", "void")
    NIGHTWAVE = ("电波", "nightwave")
    STEEL_PATH = ("钢铁之路", "steel_path")
    DUVIRI = ("双衍王境", "duviri")
    CYCLE = ("轮换", "cycle")

    def __init__(self, cn_name: str, en_name: str) -> None:
        self._cn_name = cn_name
        self._en_name = en_name

    @property
    def cn_name(self) -> str:
        """中文名称"""
        return self._cn_name

    @property
    def en_name(self) -> str:
        """英文名称"""
        return self._en_name

    @classmethod
    def from_en_name(cls, en_name: str) -> SubscribeEnums:
        """根据英文名称获取枚举成员"""
        mapping = {m.en_name: m for m in cls}
        return mapping.get(en_name.lower(), cls.ALERTS)
