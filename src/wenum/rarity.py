"""Rarity Enum / 稀有度枚举"""
from __future__ import annotations

from enum import Enum


class RarityEnum(Enum):
    """Warframe 物品稀有度枚举"""

    COMMON = ("常见", "Common", 0)
    UNCOMMON = ("罕见", "Uncommon", 1)
    RARE = ("稀有", "Rare", 2)
    LEGENDARY = ("传说", "Legendary", 3)

    def __init__(self, cn_name: str, en_name: str, tier: int) -> None:
        self._cn_name = cn_name
        self._en_name = en_name
        self._tier = tier

    @property
    def cn_name(self) -> str:
        """中文名称"""
        return self._cn_name

    @property
    def en_name(self) -> str:
        """英文名称"""
        return self._en_name

    @property
    def tier(self) -> int:
        """稀有度等级"""
        return self._tier

    @classmethod
    def from_en_name(cls, en_name: str) -> RarityEnum:
        """根据英文名称获取枚举成员"""
        mapping = {m.en_name.lower(): m for m in cls}
        return mapping.get(en_name.lower(), cls.COMMON)
