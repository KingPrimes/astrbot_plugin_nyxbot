"""Rarity Enum / 稀有度枚举"""
from __future__ import annotations

from enum import StrEnum, unique


@unique
class RarityEnum(StrEnum):
    """Warframe 物品稀有度枚举 — value = 成员名称字符串"""

    COMMON = ("COMMON", "常见", "Common", 0)
    UNCOMMON = ("UNCOMMON", "罕见", "Uncommon", 1)
    RARE = ("RARE", "稀有", "Rare", 2)
    LEGENDARY = ("LEGENDARY", "传说", "Legendary", 3)

    def __new__(cls, value: str, cn_name: str, en_name: str, tier: int):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj._cn_name = cn_name  # type: ignore
        obj._en_name = en_name  # type: ignore
        obj._tier = tier  # type: ignore
        return obj

    @property
    def cn_name(self) -> str:
        """中文名称"""
        return self._cn_name  # type: ignore

    @property
    def en_name(self) -> str:
        """英文名称"""
        return self._en_name  # type: ignore

    @property
    def tier(self) -> int:
        """稀有度等级"""
        return self._tier  # type: ignore

    @classmethod
    def from_en_name(cls, en_name: str) -> RarityEnum:
        """根据英文名称获取枚举成员"""
        mapping = {m.en_name.lower(): m for m in cls}
        return mapping.get(en_name.lower(), cls.COMMON)
