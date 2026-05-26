"""
Modifier Type Enum / 突击任务限定条件枚举
包含星际战甲中突击任务的所有限定条件名称。

Members count: 30
"""
from __future__ import annotations

from enum import StrEnum


class ModifierTypeEnum(StrEnum):
    """突击限定条件枚举 / Sortie Modifier Type Enum

    value = 中文显示名称字符串。
    SORTIE_MODIFIER_POISON 为 SORTIE_MODIFIER_TOXIN 的别名。
    """

    # === 环境危害 / Environmental Hazards ===
    SORTIE_MODIFIER_HAZARD_RADIATION = "辐射灾害"
    SORTIE_MODIFIER_HAZARD_MAGNETIC = "电磁异常"
    SORTIE_MODIFIER_HAZARD_FOG = "浓雾"
    SORTIE_MODIFIER_HAZARD_FIRE = "环境危害︰火災"
    SORTIE_MODIFIER_HAZARD_ICE = "低温外泄"
    SORTIE_MODIFIER_HAZARD_COLD = "极度寒冷"

    # === 敌人物理强化 / Enemy Physical Enhancement ===
    SORTIE_MODIFIER_SLASH = "敌人物理强化(切割)"
    SORTIE_MODIFIER_IMPACT = "敌人物理强化(冲击)"
    SORTIE_MODIFIER_PUNCTURE = "敌人物理强化(穿刺)"

    # === 敌人元素强化 / Enemy Elemental Enhancement ===
    SORTIE_MODIFIER_MAGNETIC = "敌人元素强化(磁力)"
    SORTIE_MODIFIER_EXPLOSION = "敌人元素强化(爆炸)"
    SORTIE_MODIFIER_CORROSIVE = "敌人元素强化(腐蚀)"
    SORTIE_MODIFIER_VIRAL = "敌人元素强化(病毒)"
    SORTIE_MODIFIER_ELECTRICITY = "敌人元素强化(电击)"
    SORTIE_MODIFIER_RADIATION = "敌人元素强化(辐射)"
    SORTIE_MODIFIER_GAS = "敌人元素强化(毒气)"
    SORTIE_MODIFIER_FIRE = "敌人元素强化(火焰)"
    SORTIE_MODIFIER_FREEZE = "敌人元素强化(冰冻)"
    SORTIE_MODIFIER_TOXIN = "敌人元素强化(毒素)"
    SORTIE_MODIFIER_POISON = SORTIE_MODIFIER_TOXIN

    # === 敌人防御强化 / Enemy Defense Enhancement ===
    SORTIE_MODIFIER_SHIELDS = "敌人护盾强化"
    SORTIE_MODIFIER_ARMOR = "敌人护甲强化"

    # === 武器限定 / Weapon Restrictions ===
    SORTIE_MODIFIER_BOW_ONLY = "仅限弓箭/弩"
    SORTIE_MODIFIER_SHOTGUN_ONLY = "仅限霰弹枪"
    SORTIE_MODIFIER_RIFLE_ONLY = "仅限突击步枪"
    SORTIE_MODIFIER_SECONDARY_ONLY = "武器限定：次要武器"
    SORTIE_MODIFIER_SNIPER_ONLY = "武器限定：狙击枪"
    SORTIE_MODIFIER_MELEE_ONLY = "武器限定：近战"

    # === 其他 / Others ===
    SORTIE_MODIFIER_EXIMUS = "卓越者大本营"
    SORTIE_MODIFIER_LOW_ENERGY = "能量上限减少"

    @classmethod
    def _missing_(cls, value):
        """支持通过成员名称字符串匹配 Pydantic 验证 / Support name-based matching for Pydantic validation"""
        if isinstance(value, str):
            try:
                return cls[value]
            except KeyError:
                pass
        return None
