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

#: 基础伤害词条（正式名）。
DAMAGE_ATTR = "伤害/近战伤害"

#: 元素伤害词条。词条名与 ``damagePerShot`` 的类型名完全一致，
#: 因此同类元素可以直接按名字相加，不需要额外映射表。
ELEMENT_ATTRS: frozenset[str] = frozenset({
    "冰冻伤害", "毒素伤害", "电击伤害", "火焰伤害",
    "爆炸伤害", "腐蚀伤害", "毒气伤害", "磁力伤害", "辐射伤害", "病毒伤害",
})

#: 复合元素：两种基础元素组合后的名字。
#: 组合顺序依赖 mod 排列（左上优先），数据层没有 mod 顺序信息，
#: 所以只给提示、不展示组合后的数值（§3.2）。
COMPOSITES: dict[frozenset[str], str] = {
    frozenset({"冰冻伤害", "毒素伤害"}): "病毒",
    frozenset({"电击伤害", "毒素伤害"}): "腐蚀",
    frozenset({"火焰伤害", "冰冻伤害"}): "爆炸",
    frozenset({"火焰伤害", "电击伤害"}): "辐射",
    frozenset({"电击伤害", "冰冻伤害"}): "磁力",
    frozenset({"火焰伤害", "毒素伤害"}): "毒气",
}


def short_element(name: str) -> str:
    """伤害类型名 → 图例短名：``火焰伤害`` → ``火焰``。"""
    return name[:-2] if name.endswith("伤害") else name


@dataclass(frozen=True)
class ElementShare:
    """构成条里的一段伤害。

    ``source`` 决定颜色与标注：

    * ``weapon`` —— 武器自带，灰蓝色系；
    * ``riven_new`` —— 紫卡新增的异类元素，紫色追加在条尾，标 ``(紫卡)``；
    * ``riven_same`` —— 紫卡词条与自带元素同类，并入该段，标 ``(+166.2)``。
    """

    name: str
    value: float
    source: str = "weapon"
    added: float = 0.0

    @property
    def label(self) -> str:
        """图例文案。"""
        text = f"{short_element(self.name)} {self.value:,.1f}"
        if self.source == "riven_new":
            return f"{text} (紫卡)"
        if self.source == "riven_same":
            return f"{text} ({self.added:+,.1f})"
        return text

    @property
    def from_riven(self) -> bool:
        return self.source != "weapon"


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


def build_elements(
    profile: WeaponProfile,
    attributes,
    damage_bonus: float,
) -> list[ElementShare]:
    """把武器自带伤害与紫卡元素词条合并成构成条的分段。

    两条口径（§4.3）：

    1. 元素词条的基数是**修改后的基础伤害**（含 +伤害% 词条），不是该元素原值；
    2. 自带元素也按 ``1 + Σ伤害%`` 缩放，否则构成条的总和与估算的单发总伤害
       对不上——玩家一眼就能看出两个数字打架。

    Args:
        profile: 武器属性快照。
        attributes: 词条结果（取 ``name`` / ``attr``）。
        damage_bonus: Σ 伤害词条的百分比。

    Returns:
        分段列表；武器没有任何伤害数据时返回空列表。
    """
    scale = 1 + damage_bonus / 100
    shares = [
        ElementShare(name=name, value=value * scale)
        for name, value in profile.damage_per_shot
        if value > 0
    ]
    index = {share.name: position for position, share in enumerate(shares)}
    base_damage = (profile.total_damage or 0) * scale

    for attr in attributes or []:
        if attr.name not in ELEMENT_ATTRS or not attr.attr:
            continue
        added = base_damage * attr.attr / 100
        position = index.get(attr.name)
        if position is None:
            index[attr.name] = len(shares)
            shares.append(ElementShare(attr.name, added, "riven_new", added))
        else:
            current = shares[position]
            shares[position] = ElementShare(
                current.name, current.value + added, "riven_same", added
            )
    return shares


def element_hints(shares: list[ElementShare]) -> list[str]:
    """紫卡元素与自带元素能组合成什么（只提示，不给数值）。

    §3.2：复合元素的组合顺序依赖 mod 排列，数据层没有 mod 顺序信息，
    算不准就不算。
    """
    owned = [share.name for share in shares if not share.from_riven]
    added = [share.name for share in shares if share.source == "riven_new"]
    hints: list[str] = []
    for riven_name in added:
        for own in owned:
            composite = COMPOSITES.get(frozenset({riven_name, own}))
            if composite:
                hints.append(
                    f"可与 {short_element(own)} 组合为 {composite}"
                )
    return hints


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
