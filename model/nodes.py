"""
Nodes Model / 节点模型
包含星图节点基本信息
"""
from typing import Optional
from sqlmodel import SQLModel,Field
from ..wenum import FactionEnum, MissionTypeEnum


# faction_index → FactionEnum 映射
_FACTION_INDEX_MAP: dict[int, FactionEnum] = {
    0: FactionEnum.FC_GRINEER,
    1: FactionEnum.FC_CORPUS,
    2: FactionEnum.FC_INFESTATION,
    3: FactionEnum.FC_OROKIN,
    4: FactionEnum.FC_CORRUPTED,
    5: FactionEnum.FC_SENTIENT,
    6: FactionEnum.FC_NARMER,
    7: FactionEnum.FC_MURMUR,
    8: FactionEnum.FC_SCALDRA,
    9: FactionEnum.FC_TECHROT,
    10: FactionEnum.FC_DUVIRI,
    11: FactionEnum.FC_MITW,
    12: FactionEnum.FC_TENNO,
}

# mission_index → MissionTypeEnum 映射
_MISSION_INDEX_MAP: dict[int, MissionTypeEnum] = {
    0: MissionTypeEnum.MT_ASSASSINATION,
    1: MissionTypeEnum.MT_EXTERMINATION,
    2: MissionTypeEnum.MT_SURVIVAL,
    3: MissionTypeEnum.MT_RESCUE,
    4: MissionTypeEnum.MT_SABOTAGE,
    5: MissionTypeEnum.MT_CAPTURE,
    7: MissionTypeEnum.MT_INTEL,
    8: MissionTypeEnum.MT_DEFENSE,
    9: MissionTypeEnum.MT_MOBILE_DEFENSE,
    10: MissionTypeEnum.MT_PVP,
    11: MissionTypeEnum.MT_SECTOR,
    13: MissionTypeEnum.MT_TERRITORY,
    14: MissionTypeEnum.MT_RETRIEVAL,
    15: MissionTypeEnum.MT_HIVE,
    17: MissionTypeEnum.MT_EXCAVATE,
    21: MissionTypeEnum.MT_SALVAGE,
    22: MissionTypeEnum.MT_ARENA,
    24: MissionTypeEnum.MT_PURSUIT,
    25: MissionTypeEnum.MT_PURSUIT,
    26: MissionTypeEnum.MT_ASSAULT,
    27: MissionTypeEnum.MT_EVACUATION,
    28: MissionTypeEnum.MT_LANDSCAPE,
    31: MissionTypeEnum.MT_LANDSCAPE,
    32: MissionTypeEnum.MT_ARTIFACT,
    33: MissionTypeEnum.MT_ARTIFACT,
    34: MissionTypeEnum.MT_VOID_FLOOD,
    35: MissionTypeEnum.MT_VOID_CASCADE,
    36: MissionTypeEnum.MT_VOID_ARMAGEDDON,
    38: MissionTypeEnum.MT_ALCHEMY,
    39: MissionTypeEnum.MT_CAMBIRE,
    40: MissionTypeEnum.MT_LEGACYTE_HARVEST,
    41: MissionTypeEnum.MT_SHRINE_DEFENSE,
    42: MissionTypeEnum.MT_FACEOFF,
    60: MissionTypeEnum.MT_SKIRMISH,
    61: MissionTypeEnum.MT_VOLATILE,
    62: MissionTypeEnum.MT_ORPHEUS,
    90: MissionTypeEnum.MT_ASCENSION,
    100: MissionTypeEnum.MT_RELAY,
}



class Nodes(SQLModel, table=True):
    """星图节点"""
    
    __table_args__ = {'extend_existing': True}
    
    unique_name:str = Field(primary_key=True,unique=True,alias="uniqueName",description="唯一标识")
    name:str = Field(alias="name",description="节点名称")
    system_name:Optional[str] = Field(default=None,alias="systemName",description="星系名称")
    system_index:Optional[int] = Field(default=None,alias="systemIndex",description="星系索引")
    node_type:Optional[int] = Field(default=None,alias="nodeType",description="节点类型")
    mastery_req:Optional[int] = Field(default=None,alias="masteryReq",description="段位需求")
    mission_index:Optional[int] = Field(default=None,alias="missionIdex",description="任务类型索引")
    faction_index:Optional[int] = Field(default=None,alias="facionIndex",description="派系索引")
    min_enemy_level:Optional[int] = Field(default=None,alias="minEnemyLevel",description="最低敌人等级")
    max_enemy_level:Optional[int] = Field(default=None,alias="maxEnemyLevel",description="最高敌人等级")
    
    @property
    def faction(self) -> FactionEnum:
        """根据 faction_index 获取派系枚举"""
        if self.faction_index is not None:
            return _FACTION_INDEX_MAP.get(self.faction_index, FactionEnum.FC_NONE)
        return FactionEnum.FC_NONE

    @property
    def mission_type(self) -> MissionTypeEnum:
        """根据 mission_index 获取任务类型枚举"""
        if self.mission_index is not None:
            return _MISSION_INDEX_MAP.get(
                self.mission_index, MissionTypeEnum.MT_DEFAULT
            )
        return MissionTypeEnum.MT_DEFAULT