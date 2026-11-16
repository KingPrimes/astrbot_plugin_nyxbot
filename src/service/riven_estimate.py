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
#: 名字带「伤害」后缀，与 ``damagePerShot`` 的类型名对齐，才能与武器自带
#: 的复合元素按名合并；展示时由 :func:`short_element` 去掉后缀。
COMPOSITES: dict[frozenset[str], str] = {
    frozenset({"冰冻伤害", "毒素伤害"}): "病毒伤害",
    frozenset({"电击伤害", "毒素伤害"}): "腐蚀伤害",
    frozenset({"火焰伤害", "冰冻伤害"}): "爆炸伤害",
    frozenset({"火焰伤害", "电击伤害"}): "辐射伤害",
    frozenset({"电击伤害", "冰冻伤害"}): "磁力伤害",
    frozenset({"火焰伤害", "毒素伤害"}): "毒气伤害",
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
    melee: bool = False
    """近战武器。近战没有弹匣 / 多重射击，属性区与 DPS 口径都不同。"""

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


def combine_riven_elements(items: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """把紫卡自己的元素按卡面顺序两两组合成复合元素。

    一张紫卡就是一个 mod：它的两条元素词条在游戏里必然先互相组合
    （mod 内部优先级），再与武器自带元素相加。所以紫卡带「毒素 + 电击」时，
    构成条与估算都应按「腐蚀」这一条算，而不是两条独立元素。

    跨 mod 的组合（紫卡元素 vs 武器自带元素）仍然算不准——那取决于 mod
    排列顺序，数据层没有这个信息，只给提示。但**紫卡内部**的顺序就是
    卡面从上到下的顺序，OCR 已按这个顺序给出词条，因此可以算准。

    组合规则：按顺序取第一个元素，与后面第一个能组合的元素合并成复合元素，
    复合元素不再参与后续组合（游戏里复合元素也不会再与基础元素组合）。

    Args:
        items: ``(元素名, 数值)``，按卡面顺序。

    Returns:
        组合后的 ``(元素名, 数值)`` 列表。
    """
    result = list(items)
    index = 0
    while index < len(result):
        for other in range(index + 1, len(result)):
            composite = COMPOSITES.get(
                frozenset({result[index][0], result[other][0]})
            )
            if composite is None:
                continue
            result[index] = (composite, result[index][1] + result[other][1])
            del result[other]
            break
        index += 1
    return result


def build_elements(
    profile: WeaponProfile,
    attributes,
    damage_bonus: float,
) -> list[ElementShare]:
    """把武器自带伤害与紫卡元素词条合并成构成条的分段。

    三条口径（§4.3 + 紫卡内部复合）：

    1. 元素词条的基数是**修改后的基础伤害**（含 +伤害% 词条），不是该元素原值；
    2. 自带元素也按 ``1 + Σ伤害%`` 缩放，否则构成条的总和与估算的单发总伤害
       对不上——玩家一眼就能看出两个数字打架；
    3. 紫卡自己的两条元素词条先按卡面顺序组合成复合元素，再并入构成条。

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

    riven_items = [
        (attr.name, base_damage * attr.attr / 100)
        for attr in attributes or []
        if attr.name in ELEMENT_ATTRS and attr.attr
    ]
    for name, added in combine_riven_elements(riven_items):
        position = index.get(name)
        if position is None:
            index[name] = len(shares)
            shares.append(ElementShare(name, added, "riven_new", added))
        else:
            current = shares[position]
            shares[position] = ElementShare(
                current.name, current.value + added, "riven_same", added
            )
    return shares


def element_hints(shares: list[ElementShare]) -> list[str]:
    """紫卡元素与自带元素能组合成什么（只提示，不给数值）。

    跨 mod 的组合顺序依赖 mod 排列（左上优先），数据层没有这个信息，
    算不准就不算——这里只给「可以这么配」的提示。
    紫卡**内部**的两条元素已经在 :func:`combine_riven_elements` 里算过了，
    组合后的复合元素不会再出现在提示里。
    """
    owned = [share.name for share in shares if not share.from_riven]
    added = [share.name for share in shares if share.source == "riven_new"]
    hints: list[str] = []
    for riven_name in added:
        for own in owned:
            composite = COMPOSITES.get(frozenset({riven_name, own}))
            if composite:
                hints.append(
                    f"可与 {short_element(own)} 组合为 {short_element(composite)}"
                )
    return hints


# ---------------------------------------------------------------- 四步估算

#: 暴击率词条 / 暴击伤害词条的正式名。
CRIT_CHANCE_ATTR = "暴击几率"
CRIT_DAMAGE_ATTR = "暴击伤害"

#: 近战特殊攻击词条（§6.5）。震地 / 重击各走一条独立估算分支。
SLAM_ATTR = "震地攻击伤害"
HEAVY_ATTR = "重击伤害"


@dataclass(frozen=True)
class RivenEstimate:
    """紫卡加成后的面板等效估算（§4.2 四步链路）。

    每一步都是「能算到哪算到哪」：输入缺失的那一步整行不画，
    并在 ``skipped`` 里登记，**不回退成 0 假装算过**。
    """

    base_damage: float
    """第 1 步：``totalDamage × (1 + Σ伤害%)``。"""
    total_damage: float
    """第 2 步：``基础伤害' × (1 + Σ元素%)``。"""
    per_shot: float
    """第 3 步：单发期望（含暴击）。"""
    dps: float | None
    """第 4 步：持续 DPS；无射速 / 弹匣 / 装填时为 ``None``。"""
    baseline_per_shot: float
    """无紫卡时的单发期望（算加成幅度的分母）。"""
    baseline_dps: float | None
    damage_bonus: float
    element_bonus: float
    crit_chance: float
    """夹到 1.0 之后的暴击率。"""
    crit_multiplier: float
    crit_factor: float
    """``1 + 暴击率 × (暴击倍率 - 1)``。"""
    fire_rate: float | None
    multishot: float
    duty: float | None
    """装填占空比 ``弹匣 / (弹匣 + 装填 × 射速)``。"""
    slam: float | None = None
    """震地攻击的单发期望（近战专属）。"""
    heavy: float | None = None
    """重击的单发期望（近战专属）。"""
    baseline_slam: float | None = None
    baseline_heavy: float | None = None
    skipped: tuple[str, ...] = ()

    @property
    def per_shot_gain(self) -> float:
        """单发期望相对无紫卡的提升百分比。"""
        if not self.baseline_per_shot:
            return 0.0
        return (self.per_shot / self.baseline_per_shot - 1) * 100

    @property
    def dps_gain(self) -> float | None:
        """DPS 相对无紫卡的提升百分比。"""
        if not self.dps or not self.baseline_dps:
            return None
        return (self.dps / self.baseline_dps - 1) * 100

    @property
    def slam_gain(self) -> float | None:
        if not self.slam or not self.baseline_slam:
            return None
        return (self.slam / self.baseline_slam - 1) * 100

    @property
    def heavy_gain(self) -> float | None:
        if not self.heavy or not self.baseline_heavy:
            return None
        return (self.heavy / self.baseline_heavy - 1) * 100

    @property
    def element_factor(self) -> float:
        return 1 + self.element_bonus / 100


def _sum_attr(attributes, name: str) -> float:
    return sum(attr.attr for attr in attributes or [] if attr.name == name)


def build_estimate(profile: WeaponProfile | None, attributes) -> RivenEstimate | None:
    """按 §4.2 的四步链路算估算值。

    ::

        基础伤害'  = totalDamage × (1 + Σ伤害词条%)
        单发总伤害 = 基础伤害' × (1 + Σ元素词条%)
        单发期望   = 单发总伤害 × (1 + 暴击率' × (暴击倍率' - 1))
        持续 DPS   = 单发期望 × 射速 × 多重 × 装填占空比

    * 元素词条以修改后的基础伤害为基数；
    * ``暴击率' = min(原暴击率 + Σ暴击率词条, 1.0)``，超出部分记「未计」；
    * 多重按等效乘算（独立弹丸，期望可加）。

    Args:
        profile: 武器属性快照。
        attributes: 词条结果。

    Returns:
        估算结果；连基础伤害都没有时返回 ``None``（画不出任何有意义的数）。
    """
    if profile is None or not profile.total_damage:
        return None

    damage_bonus = _sum_attr(attributes, DAMAGE_ATTR)
    element_bonus = sum(
        attr.attr for attr in attributes or [] if attr.name in ELEMENT_ATTRS
    )
    base_damage = profile.total_damage * (1 + damage_bonus / 100)
    total_damage = base_damage * (1 + element_bonus / 100)

    skipped: list[str] = []
    if profile.critical_chance is None or profile.critical_multiplier is None:
        crit_chance = 0.0
        crit_multiplier = 1.0
        crit_factor = 1.0
        skipped.append("暴击")
        base_crit_factor = 1.0
    else:
        raw_chance = profile.critical_chance + _sum_attr(attributes, CRIT_CHANCE_ATTR) / 100
        crit_chance = min(raw_chance, 1.0)
        if raw_chance > 1.0:
            skipped.append("暴击率溢出")
        crit_multiplier = profile.critical_multiplier * (
            1 + _sum_attr(attributes, CRIT_DAMAGE_ATTR) / 100
        )
        crit_factor = 1 + crit_chance * (crit_multiplier - 1)
        base_crit_factor = 1 + profile.critical_chance * (
            profile.critical_multiplier - 1
        )

    per_shot = total_damage * crit_factor
    baseline_per_shot = profile.total_damage * base_crit_factor

    # 近战分支：震地 / 重击各自算一条，词条加成叠加在通用 +伤害% 之上。
    # 两段震地（直接命中 + 范围冲击波，随距离衰减）的公式还没钉死，
    # 只算直接命中，并在「未计」里说明范围伤害没算。
    slam: float | None = None
    heavy: float | None = None
    baseline_slam: float | None = None
    baseline_heavy: float | None = None
    element_factor = 1 + element_bonus / 100
    if profile.slam_attack:
        slam_bonus = damage_bonus + _sum_attr(attributes, SLAM_ATTR)
        slam = profile.slam_attack * (1 + slam_bonus / 100) * element_factor * crit_factor
        baseline_slam = profile.slam_attack * base_crit_factor
    else:
        skipped.append("震地")
    if profile.heavy_attack_damage:
        heavy_bonus = damage_bonus + _sum_attr(attributes, HEAVY_ATTR)
        heavy = (
            profile.heavy_attack_damage
            * (1 + heavy_bonus / 100)
            * element_factor
            * crit_factor
        )
        baseline_heavy = profile.heavy_attack_damage * base_crit_factor
    else:
        skipped.append("重击")
    if profile.slam_radial_damage:
        skipped.append("震地范围伤害")

    fire_rate = profile.fire_rate
    multishot = float(profile.multishot or 1)
    duty: float | None = None
    dps: float | None = None
    baseline_dps: float | None = None
    if profile.melee:
        # 近战没有弹匣 / 装填 / 多重：持续 DPS 就是「单次期望 × 攻击速度」，
        # 不乘装填占空比（那会把近战 DPS 算低一个量级）。
        if fire_rate and fire_rate > 0:
            dps = per_shot * fire_rate
            baseline_dps = baseline_per_shot * fire_rate
        else:
            skipped.append("持续 DPS")
    elif (
        fire_rate
        and profile.magazine_size
        and profile.reload_time is not None
        and fire_rate > 0
    ):
        duty = profile.magazine_size / (
            profile.magazine_size + profile.reload_time * fire_rate
        )
        dps = per_shot * fire_rate * multishot * duty
        baseline_dps = baseline_per_shot * fire_rate * multishot * duty
    else:
        skipped.append("持续 DPS")

    return RivenEstimate(
        base_damage=base_damage,
        total_damage=total_damage,
        per_shot=per_shot,
        dps=dps,
        baseline_per_shot=baseline_per_shot,
        baseline_dps=baseline_dps,
        damage_bonus=damage_bonus,
        element_bonus=element_bonus,
        crit_chance=crit_chance,
        crit_multiplier=crit_multiplier,
        crit_factor=crit_factor,
        fire_rate=fire_rate,
        multishot=multishot,
        duty=duty,
        slam=slam,
        heavy=heavy,
        baseline_slam=baseline_slam,
        baseline_heavy=baseline_heavy,
        skipped=tuple(skipped),
    )


def profile_from_weapon(weapon: Weapons, *, melee: bool = False) -> WeaponProfile:
    """把 ``Weapons`` 模型转成只读快照。

    ``damagePerShot`` 走模型自带的解析（JSON 阵列 → 中文类型名 + 数值），
    解析失败时返回空元组，不抛异常——一张卡不值得因为脏数据崩掉。

    字段一律 ``getattr`` 读取：单测用轻量替身、旧版本模型都可能少几个
    近战字段，缺字段按「无此属性」处理即可，不该让整张卡崩掉。

    Args:
        weapon: 武器模型（或其轻量替身）。
        melee: 是否近战武器。由调用方按 ``productCategory`` 判定——
            近战的 ``fireRate`` 是攻击速度、没有多重射击，
            渲染与估算都要走另一套口径。
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
        melee=melee,
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
