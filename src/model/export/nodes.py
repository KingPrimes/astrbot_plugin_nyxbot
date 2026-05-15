"""
Nodes Model (exprot) / 星图节点模型（导出数据）

对应 Java: Nodes.java (exprot)
"""
from __future__ import annotations

from tortoise import fields
from tortoise.models import Model

from ...wenum import FactionEnum, MissionTypeEnum

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


class ExprotNodes(Model):
    """星图节点（导出数据）"""

    uniqueName = fields.CharField(max_length=255, pk=True, source_field="unique_name", description="唯一标识")
    name = fields.CharField(max_length=255, description="节点名称")
    systemName = fields.CharField(max_length=255, null=True, source_field="system_name", description="星系名称")
    systemIndex = fields.IntField(null=True, source_field="system_index", description="星系索引")
    nodeType = fields.IntField(null=True, source_field="node_type", description="节点类型")
    masteryReq = fields.IntField(null=True, source_field="mastery_req", description="段位需求")
    missionIndex = fields.IntField(null=True, source_field="mission_index", description="任务类型索引")
    factionIndex = fields.IntField(null=True, source_field="faction_index", description="派系索引")
    minEnemyLevel = fields.IntField(null=True, source_field="min_enemy_level", description="最低敌人等级")
    maxEnemyLevel = fields.IntField(null=True, source_field="max_enemy_level", description="最高敌人等级")

    class Meta:
        table = "exprotnodes"

    @property
    def faction(self) -> FactionEnum:
        """根据 factionIndex 获取派系枚举"""
        if self.factionIndex is not None:
            return _FACTION_INDEX_MAP.get(self.factionIndex, FactionEnum.FC_NONE)
        return FactionEnum.FC_NONE

    @property
    def mission_type(self) -> MissionTypeEnum:
        """根据 missionIndex 获取任务类型枚举"""
        if self.missionIndex is not None:
            return _MISSION_INDEX_MAP.get(
                self.missionIndex, MissionTypeEnum.MT_DEFAULT
            )
        return MissionTypeEnum.MT_DEFAULT
