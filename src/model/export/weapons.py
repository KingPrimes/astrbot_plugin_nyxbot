"""
Weapons Model / 武器模型

对应 Java: Weapons.java
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum

from tortoise import fields
from tortoise.models import Model

from ...util import to_title_case


class ProductCategory(str, Enum):
    """武器分类"""

    PISTOLS = "Pistols"
    LONG_GUNS = "LongGuns"
    MELEE = "Melee"
    SPACE_GUNS = "SpaceGuns"
    SPACE_MELEE = "SpaceMelee"
    SPECIAL_ITEMS = "SpecialItems"
    CREW_SHIP_WEAPONS = "CrewShipWeapons"
    SENTINEL_WEAPONS = "SentinelWeapons"
    SHOTGUNS = "Shotguns"

    @property
    def display_name(self) -> str:
        _names = {
            ProductCategory.PISTOLS: "次要武器",
            ProductCategory.LONG_GUNS: "主要武器",
            ProductCategory.MELEE: "近战武器",
            ProductCategory.SPACE_GUNS: "Archwing武器",
            ProductCategory.SPACE_MELEE: "Archwing近战武器",
            ProductCategory.SPECIAL_ITEMS: "显赫武器",
            ProductCategory.CREW_SHIP_WEAPONS: "星舰武器",
            ProductCategory.SENTINEL_WEAPONS: "守护武器",
            ProductCategory.SHOTGUNS: "霰弹枪",
        }
        return _names.get(self, self.value)


@dataclass
class DamagePerShot:
    """武器伤害类型与数值。"""
    name: str
    damage: float


# 伤害阵列索引 → 中文名称映射
_DAMAGE_TYPE_NAMES: list[str] = [
    "冲击伤害", "穿刺伤害", "切割伤害", "火焰伤害", "冰冻伤害", "电击伤害", "毒素伤害",
    "爆炸伤害", "辐射伤害", "毒气伤害", "磁力伤害", "病毒伤害", "腐蚀伤害", "虚空伤害",
    "Tau伤害", "DT_CINEMATIC", "DT_SHIELD_DRAIN", "DT_HEALTH_DRAIN", "DT_ENERGY_DRAIN",
    "真实伤害",
]


class Weapons(Model):
    """武器数据"""

    uniqueName = fields.CharField(max_length=255, pk=True, source_field="unique_name", description="武器唯一名称")
    name = fields.CharField(max_length=255, null=True, description="武器名称")
    codexSecret = fields.BooleanField(null=True, source_field="codex_secret", description="是否从资料库隐藏")
    damagePerShot = fields.TextField(null=True, source_field="damage_per_shot", description="武器伤害阵列（JSON序列化）")
    totalDamage = fields.IntField(null=True, source_field="total_damage", description="总伤害")
    description = fields.TextField(null=True, description="描述")
    englishName = fields.CharField(max_length=255, null=True, source_field="english_name", description="英文名称")
    criticalChance = fields.FloatField(null=True, source_field="critical_chance", description="暴击率")
    criticalMultiplier = fields.FloatField(null=True, source_field="critical_multiplier", description="暴击倍率")
    procChance = fields.FloatField(null=True, source_field="proc_chance", description="触发概率")
    fireRate = fields.FloatField(null=True, source_field="fire_rate", description="射速")
    masteryReq = fields.IntField(null=True, source_field="mastery_req", description="段位需求")
    productCategory = fields.CharField(max_length=100, null=True, source_field="product_category", description="武器类型")
    slot = fields.IntField(null=True, description="槽位")
    accuracy = fields.FloatField(null=True, description="精准度")
    omegaAttenuation = fields.FloatField(null=True, source_field="omega_attenuation", description="裂罅倾向")
    maxLevelCap = fields.IntField(default=30, null=True, source_field="max_level_cap", description="最大等级")
    noise = fields.CharField(max_length=100, null=True, description="噪音等级")
    trigger = fields.CharField(max_length=100, null=True, description="射击类型")
    magazineSize = fields.IntField(null=True, source_field="magazine_size", description="弹匣容量")
    reloadTime = fields.FloatField(null=True, source_field="reload_time", description="装填时间")
    sentinel = fields.BooleanField(null=True, description="是否为守护武器")
    multishot = fields.IntField(null=True, description="多重射击")

    class Meta:
        table = "weapons"

    # ── 伤害阵列解析 ──

    def get_damage_per_shot_list(self) -> list[DamagePerShot]:
        """解析 damagePerShot JSON 阵列，返回非零伤害类型与数值的列表。

        Returns:
            按索引顺序过滤掉零值后的 DamagePerShot 列表。
        """
        if not self.damagePerShot:
            return []
        try:
            values = json.loads(self.damagePerShot)
        except (json.JSONDecodeError, TypeError):
            return []
        result: list[DamagePerShot] = []
        for i, val in enumerate(values):
            if i < len(_DAMAGE_TYPE_NAMES) and val and val > 0:
                result.append(DamagePerShot(name=_DAMAGE_TYPE_NAMES[i], damage=float(val)))
        return result

    # ── 英文名称提取 ──

    def get_english_name(self) -> str:
        """从 description 中提取武器英文名称。

        解析格式：`（英文：SomeNameOrOther）` 并将每个部分首字母大写，保留原分隔符。

        Returns:
            提取的英文名称，无法提取时返回空字符串。
        """
        if not self.description or not self.description.strip():
            return ""
        m = re.search(r"（英文：(.+?)）", self.description)
        if not m:
            return ""
        raw = m.group(1)
        # 转换为每个部分首字母大写并保留分隔符：HELLO_WORLD → Hello_World
        e_name = to_title_case(raw)
        # 处理 MK1- 前缀特殊逻辑
        if self.name and self.name.upper() == "MK1-":
            if e_name and e_name != self.description.strip() and e_name.upper() != "MK1-":
                return f"Mk1-{e_name}"
        if e_name and self.description and e_name == self.description.strip():
            return ""
        return e_name

    @property
    def critical_chance_format(self) -> str:
        """格式化暴击率"""
        if self.criticalChance is not None:
            return f"{self.criticalChance * 100:.2f}"
        return "0.00"

    @property
    def proc_chance_format(self) -> str:
        """格式化触发概率"""
        if self.procChance is not None:
            return f"{self.procChance * 100:.2f}"
        return "0.00"

    @property
    def fire_rate_format(self) -> str:
        """格式化射速"""
        if self.fireRate is not None:
            return f"{self.fireRate:.2f}"
        return "0.00"

    @property
    def accuracy_format(self) -> str:
        """格式化精准度"""
        if self.accuracy is not None:
            return f"{self.accuracy:.2f}"
        return "0.00"

    @property
    def omega_attenuation_format(self) -> str:
        """格式化裂罅倾向"""
        if self.omegaAttenuation is not None:
            return f"{self.omegaAttenuation:.2f}"
        return "0.00"

    @property
    def reload_time_format(self) -> str:
        """格式化装填时间"""
        if self.reloadTime is not None:
            return f"{self.reloadTime:.2f}"
        return "0.00"


