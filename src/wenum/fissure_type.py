"""Fissure Type Enum / 裂隙类型枚举

包含裂隙任务的等级分类（FissureTier）和裂隙查询类型（FissureTypeEnum）。
"""
from __future__ import annotations

from enum import Enum


class FissureTypeEnum(Enum):
    """裂隙查询类型枚举 / Fissure Query Type Enum

    镜像 Java FissureTypeEnum:
    - ACTIVE_MISSION: 普通裂隙任务（非钢铁之路）
    - STEEL_PATH: 钢铁之路裂隙任务
    - VOID_STORMS: 虚空风暴（Railjack 裂隙）
    """

    ACTIVE_MISSION = "active_mission"
    STEEL_PATH = "steel_path"
    VOID_STORMS = "void_storms"


class FissureTier(Enum):
    """裂隙等级枚举。"""

    LITH = (1, "不朽", "Lith")
    MESO = (2, "无瑕", "Meso")
    NEO = (3, "光辉", "Neo")
    AXII = (4, "幻影", "Axi")
    REQUIEM = (5, "安魂", "Requiem")

    def __init__(self, tier_id: int, cn_name: str, en_name: str) -> None:
        self._tier_id = tier_id
        self._cn_name = cn_name
        self._en_name = en_name

    @property
    def tier_id(self) -> int:
        """裂隙等级 ID。"""
        return self._tier_id

    @property
    def cn_name(self) -> str:
        """中文名称。"""
        return self._cn_name

    @property
    def en_name(self) -> str:
        """英文名称。"""
        return self._en_name

    @classmethod
    def from_tier_id(cls, tier_id: int) -> FissureTier:
        """根据 tier ID 获取枚举成员。"""
        mapping = {m.tier_id: m for m in cls}
        return mapping.get(tier_id, cls.LITH)

    @classmethod
    def from_en_name(cls, en_name: str) -> FissureTier:
        """根据英文名称获取枚举成员。"""
        mapping = {m.en_name.lower(): m for m in cls}
        return mapping.get(en_name.lower(), cls.LITH)
