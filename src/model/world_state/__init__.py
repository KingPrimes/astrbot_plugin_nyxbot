"""WorldState model package / WorldState 响应模型包"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Reward(BaseModel):
    """任务奖励"""
    items: list[str] = []
    credits: int = 0
    counted_items: list[dict] = Field(default=[], alias="countedItems")


class AlertMission(BaseModel):
    """警报任务"""
    node: str = "未知"
    mission_type: str = Field(default="未知", alias="missionType")
    faction: str = "未知"
    min_enemy_level: int = Field(default=0, alias="minEnemyLevel")
    max_enemy_level: int = Field(default=0, alias="maxEnemyLevel")


class Alert(BaseModel):
    """警报"""
    id: str = ""
    activation: str = ""
    expiry: str = ""
    mission: Optional[AlertMission] = None
    reward: Optional[Reward] = None


class SortieVariant(BaseModel):
    """突击阶段"""
    node: str = "未知"
    mission_type: str = Field(default="未知", alias="missionType")
    modifier: str = ""
    modifier_name: str = Field(default="", alias="modifierName")


class Sortie(BaseModel):
    """突击"""
    id: str = ""
    activation: str = ""
    expiry: str = ""
    boss: str = ""
    faction: str = ""
    variants: list[SortieVariant] = []


class Fissure(BaseModel):
    """裂隙"""
    id: str = ""
    activation: str = ""
    expiry: str = ""
    node: str = "未知"
    mission_type: str = Field(default="未知", alias="missionType")
    faction: str = ""
    tier: int = 0


class Invasion(BaseModel):
    """入侵"""
    id: str = ""
    activation: str = ""
    expiry: str = ""
    node: str = "未知"
    attacker: str = ""
    defender: str = ""
    completion: float = 0


class VoidTrader(BaseModel):
    """虚空商人"""
    id: str = ""
    activation: str = ""
    expiry: str = ""
    character: str = "Baro Ki'Teer"
    location: str = "未知"


class Arbitration(BaseModel):
    """仲裁"""
    activation: str = ""
    expiry: str = ""
    node: str = "未知"
    mission_type: str = Field(default="未知", alias="missionType")
    faction: str = "未知"


class CetusCycle(BaseModel):
    """希图斯周期"""
    activation: str = ""
    expiry: str = ""
    is_day: bool = Field(default=True, alias="isDay")
    state: str = "day"


class DuviriCycle(BaseModel):
    """双衍王境周期"""
    activation: str = ""
    expiry: str = ""
    is_day: bool = Field(default=True, alias="isDay")
    state: str = ""


class DailyDeal(BaseModel):
    """每日特惠"""
    item: str = "未知"
    original_price: int = Field(default=0, alias="originalPrice")
    sale_price: int = Field(default=0, alias="salePrice")
    discount: int = 0
    total: int = 0
    sold: int = 0


class SteelPath(BaseModel):
    """钢铁之路"""
    activation: str = ""
    expiry: str = ""
    rotation: str = ""


class Nightwave(BaseModel):
    """午夜电波"""
    activation: str = ""
    expiry: str = ""
    season: int = 0
    rank: int = 0


__all__ = [
    "Reward",
    "AlertMission",
    "Alert",
    "SortieVariant",
    "Sortie",
    "Fissure",
    "Invasion",
    "VoidTrader",
    "Arbitration",
    "CetusCycle",
    "DuviriCycle",
    "DailyDeal",
    "SteelPath",
    "Nightwave",
]
