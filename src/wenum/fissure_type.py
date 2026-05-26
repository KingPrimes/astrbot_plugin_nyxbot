"""Fissure Type Enum / 裂隙类型枚举

包含裂隙任务的等级分类（FissureTier）和裂隙查询类型（FissureTypeEnum）。
"""
from __future__ import annotations

from enum import StrEnum, unique


@unique
class FissureTypeEnum(StrEnum):
    """裂隙查询类型枚举 / Fissure Query Type Enum

    镜像 Java FissureTypeEnum:
    - ACTIVE_MISSION: 普通裂隙任务（非钢铁之路）
    - STEEL_PATH: 钢铁之路裂隙任务
    - VOID_STORMS: 虚空风暴（Railjack 裂隙）
    """

    ACTIVE_MISSION = "active_mission"
    STEEL_PATH = "steel_path"
    VOID_STORMS = "void_storms"


@unique
class FissureTier(StrEnum):
    """裂隙等级枚举 — value = 成员名称字符串"""

    LITH = ("LITH", 1, "不朽", "Lith")
    MESO = ("MESO", 2, "无瑕", "Meso")
    NEO = ("NEO", 3, "光辉", "Neo")
    AXII = ("AXII", 4, "幻影", "Axi")
    REQUIEM = ("REQUIEM", 5, "安魂", "Requiem")

    def __new__(cls, value: str, tier_id: int, cn_name: str, en_name: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj._tier_id = tier_id  # type: ignore
        obj._cn_name = cn_name  # type: ignore
        obj._en_name = en_name  # type: ignore
        return obj

    @property
    def tier_id(self) -> int:
        """裂隙等级 ID"""
        return self._tier_id  # type: ignore

    @property
    def cn_name(self) -> str:
        """中文名称"""
        return self._cn_name  # type: ignore

    @property
    def en_name(self) -> str:
        """英文名称"""
        return self._en_name  # type: ignore

    @classmethod
    def from_tier_id(cls, tier_id: int) -> FissureTier:
        """根据 tier ID 获取枚举成员"""
        mapping = {m.tier_id: m for m in cls}
        return mapping.get(tier_id, cls.LITH)

    @classmethod
    def from_en_name(cls, en_name: str) -> FissureTier:
        """根据英文名称获取枚举成员"""
        mapping = {m.en_name.lower(): m for m in cls}
        return mapping.get(en_name.lower(), cls.LITH)
