"""紫卡卡片的武器数据快照与加成估算。

卡片需要武器的基础属性（基础伤害 / 暴击 / 触发 / 射速 / 多重 / 弹匣 …）
来画 L3 属性区，估算链路还要用同一批字段做四步计算。渲染层不该直接
依赖 Tortoise 模型（37 列、随时可能加字段），因此这里做一层**只读快照**：

* :class:`WeaponProfile` —— 卡片与估算共用的输入，建结果时从 ``Weapons`` 取一次；
* :func:`profile_from_weapon` —— 模型 → 快照的转换（含 ``damagePerShot`` 解析）。

设计文档：``plans/riven_analyse_card_design_2026-11-16.md`` §3.1 / §4。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..model.export.weapons import Weapons


@dataclass(frozen=True)
class WeaponProfile:
    """武器基础属性快照（卡片 L3 层 + 估算输入）。

    ``None`` 表示导出文件里没有该字段——卡片按「无此属性」处理，
    估算按「该步不成立」处理，**不回退成 0 假装算过**。
    """

    total_damage: float | None = None
    critical_chance: float | None = None
    """暴击几率，0~1 的小数（导出文件原样）。"""
    critical_multiplier: float | None = None
    proc_chance: float | None = None
    """触发几率，0~1 的小数。"""
    fire_rate: float | None = None
    multishot: int | None = None
    magazine_size: int | None = None
    reload_time: float | None = None
    accuracy: float | None = None
    mastery_req: int | None = None
    damage_per_shot: tuple[tuple[str, float], ...] = ()
    """伤害类型构成 ``(中文类型名, 数值)``，已过滤 0 值。"""

    # ── 近战专属（ExportWeapons 提供，供属性区与震地/重击估算）──
    slam_attack: int | None = None
    slam_radial_damage: int | None = None
    slam_radius: int | None = None
    heavy_attack_damage: int | None = None
    heavy_slam_attack: int | None = None
    heavy_slam_radial_damage: int | None = None
    slide_attack: int | None = None
    combo_duration: int | None = None
    attack_range: float | None = None

    @property
    def has_slam(self) -> bool:
        """是否带震地数据（近战 224/225 把有）。"""
        return bool(self.slam_attack)

    @property
    def has_heavy(self) -> bool:
        """是否带重击数据。"""
        return bool(self.heavy_attack_damage)

    def same_stats(self, other: WeaponProfile) -> bool:
        """两份快照的属性是否完全一致（用于「属性一致，仅名称不同」判定）。

        只比卡片会画出来的字段：``mastery_req`` 不同但其余相同，也算一致
        （段位单独展示，不影响属性区）。
        """
        return self == other


def profile_from_weapon(weapon: Weapons) -> WeaponProfile:
    """把 ``Weapons`` 模型转成只读快照。

    ``damagePerShot`` 走模型自带的解析（JSON 阵列 → 中文类型名 + 数值），
    解析失败时返回空元组，不抛异常——一张卡不值得因为脏数据崩掉。

    字段一律 ``getattr`` 读取：单测用轻量替身、旧版本模型都可能少几个
    近战字段，缺字段按「无此属性」处理即可，不该让整张卡崩掉。
    """
    getter = getattr(weapon, "get_damage_per_shot_list", None)
    try:
        damage = (
            tuple((item.name, item.damage) for item in getter()) if callable(getter) else ()
        )
    except Exception:  # pragma: no cover - 解析失败只影响构成条
        damage = ()

    def value(name: str):
        return getattr(weapon, name, None)

    return WeaponProfile(
        total_damage=value("totalDamage"),
        critical_chance=value("criticalChance"),
        critical_multiplier=value("criticalMultiplier"),
        proc_chance=value("procChance"),
        fire_rate=value("fireRate"),
        multishot=value("multishot"),
        magazine_size=value("magazineSize"),
        reload_time=value("reloadTime"),
        accuracy=value("accuracy"),
        mastery_req=value("masteryReq"),
        damage_per_shot=damage,
        slam_attack=value("slamAttack"),
        slam_radial_damage=value("slamRadialDamage"),
        slam_radius=value("slamRadius"),
        heavy_attack_damage=value("heavyAttackDamage"),
        heavy_slam_attack=value("heavySlamAttack"),
        heavy_slam_radial_damage=value("heavySlamRadialDamage"),
        slide_attack=value("slideAttack"),
        combo_duration=value("comboDuration"),
        attack_range=value("range"),
    )
