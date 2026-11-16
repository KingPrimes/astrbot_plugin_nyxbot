"""紫卡卡片的武器数据快照与加成估算。

卡片需要武器的基础属性（基础伤害 / 暴击 / 触发 / 射速 / 多重 / 弹匣 …）
来画 L3 属性区，估算链路还要用同一批字段做四步计算。渲染层不该直接
依赖 Tortoise 模型（37 列、随时可能加字段），因此这里做一层**只读快照**：

* :class:`WeaponProfile` —— 卡片与估算共用的输入，建结果时从 ``Weapons`` 取一次；
* :func:`profile_from_weapon` —— 模型 → 快照的转换（含 ``damagePerShot`` 解析）。

设计文档：``plans/riven_analyse_card_design_2026-11-16.md`` §3.1 / §4。
"""
from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ..model.export.weapons import Weapons
    # 估算以 ResultAttribute 为输入（鸭子类型：name / attribute_name / attr）；
    # riven_analyse 反向导入本模块，这里必须挂在 TYPE_CHECKING 下避免环。
    from .riven_analyse import ResultAttribute

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
        """两份快照是否**整体全等**（含 ``mastery_req``），用于「属性一致」判定。

        与设计稿 §10.2-8 对齐：任一字段不同（包括不在属性区单独展示的
        ``mastery_req``）都不算一致——宁可重复画一份属性，也不把两把
        段位不同的武器当成「完全一样」而吞掉差异。

        注意：不要改成「只比卡片会画的字段」。那会让仅段位不同的变体
        退化成提示行，段位信息只出现在变体卡头，属性区的数值来源会
        变得含糊。
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
    attributes: Sequence[ResultAttribute] | None,
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

#: 影响第四步（持续 DPS）的速度类词条。
#: 这些词条此前完全没有参与估算：带 +100% 射速 / +100% 多重的紫卡，
#: 算出来的 DPS 与不带时一模一样，等于在卡片上凭空抹掉了这几类词条。
RATE_ATTR = "射速/攻击速度"
MULTISHOT_ATTR = "多重射击"
MAGAZINE_ATTR = "弹匣容量"
RELOAD_ATTR = "装填速度"


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
    heavy_crit_factor: float = 1.0
    """重击用的暴击系数：重击专属词条（``重击时 x2``）的加成在此加倍。

    与普通 :attr:`crit_factor` 分开，因为「暴击几率（重击时 x2）」这类词条
    只在重击时生效——混进普通暴击率会同时把普通攻击多算、重击少算一倍。
    """

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


def _sum_attr(
    attributes: Sequence[ResultAttribute] | None, name: str
) -> float:
    return sum(attr.attr for attr in attributes or [] if attr.name == name)


def _sum_crit_attr(
    attributes: Sequence[ResultAttribute] | None, *, heavy: bool
) -> float:
    """暴击率词条按「是否重击专属」分桶求和。

    ``暴击几率（重击时 x2）`` 的正式名（``name``）与普通暴击几率相同，
    区别只在 OCR 展示名（``attribute_name``）里带「重击」二字，所以分桶
    必须看展示名。
    """
    total = 0.0
    for attr in attributes or []:
        if attr.name != CRIT_CHANCE_ATTR:
            continue
        if ("重击" in (attr.attribute_name or "")) == heavy:
            total += attr.attr
    return total


def build_estimate(
    profile: WeaponProfile | None,
    attributes: Sequence[ResultAttribute] | None,
) -> RivenEstimate | None:
    """按 §4.2 的四步链路算估算值。

    ::

        基础伤害'  = totalDamage × (1 + Σ伤害词条%)
        单发总伤害 = 基础伤害' × (1 + Σ元素词条%)
        单发期望   = 单发总伤害 × (1 + 暴击率' × (暴击倍率' - 1))
        持续 DPS   = 单发期望 × 射速' × 多重' × 装填占空比'

    * 带撇号的量都含紫卡词条：射速' / 攻击速度'、多重'、弹匣'、装填时间'
      （装填速度 +X% → 时间 ÷ (1 + X%)）；不带撇号的只用于算 baseline；
    * 元素词条以修改后的基础伤害为基数；
    * 词条百分比一律**相对于基础值**（wiki ``Total = Base × (1 + Σ Bonus)``），
      不是直接加到最终值上的百分点；
    * ``暴击率' = min(原暴击率 × (1 + Σ暴击率词条%), 1.0)``，超出部分记「未计」；
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
        heavy_crit_factor = 1.0
        skipped.append("暴击")
        base_crit_factor = 1.0
    else:
        # 暴击率词条是**相对基础暴击率**的加成（wiki：Braton 12% 配 Point Strike
        # +150% 与 Argon Scope +135% 得 12% × (1 + 150% + 135%) = 46.2%），
        # 不是往最终值上加百分点。写成加法会把 20% + 50% 算成 70%（应为 30%）。
        # 重击专属词条（卡面「重击时 x2」）只在重击时生效且加成翻倍，
        # 不能混进普通暴击率——否则普通攻击被多算、重击又少算一倍。
        normal_bonus = _sum_crit_attr(attributes, heavy=False)
        heavy_only_bonus = _sum_crit_attr(attributes, heavy=True)

        raw_chance = profile.critical_chance * (1 + normal_bonus / 100)
        # 上下界都要夹：负词条足够大时 raw_chance 会变负，代入
        # ``1 + chance × (倍率 - 1)`` 会算出负的暴击系数，卡片上就是负伤害
        # （实测 20% 基础配 -150% 词条 → chance -1.3、单发期望 -30）。
        crit_chance = min(max(raw_chance, 0.0), 1.0)
        if raw_chance > 1.0:
            skipped.append("暴击率溢出")
        crit_multiplier = profile.critical_multiplier * (
            1 + _sum_attr(attributes, CRIT_DAMAGE_ATTR) / 100
        )
        crit_factor = 1 + crit_chance * (crit_multiplier - 1)

        raw_heavy_chance = profile.critical_chance * (
            1 + (normal_bonus + 2 * heavy_only_bonus) / 100
        )
        heavy_crit_chance = min(max(raw_heavy_chance, 0.0), 1.0)
        if raw_heavy_chance > 1.0 and raw_chance <= 1.0:
            skipped.append("重击暴击率溢出")
        heavy_crit_factor = 1 + heavy_crit_chance * (crit_multiplier - 1)

        base_crit_factor = 1 + profile.critical_chance * (
            profile.critical_multiplier - 1
        )

    per_shot = total_damage * crit_factor
    baseline_per_shot = profile.total_damage * base_crit_factor

    # 近战分支：震地 / 重击各自算一条，词条加成叠加在通用 +伤害% 之上。
    # 两段震地（直接命中 + 范围冲击波，随距离衰减）的公式还没钉死，
    # 只算直接命中，并在「未计」里说明范围伤害没算。
    # 枪械根本没有震地 / 重击，不登记「未计」——那是噪音，不是缺失。
    slam: float | None = None
    heavy: float | None = None
    baseline_slam: float | None = None
    baseline_heavy: float | None = None
    element_factor = 1 + element_bonus / 100
    if profile.melee:
        if profile.slam_attack:
            slam_bonus = damage_bonus + _sum_attr(attributes, SLAM_ATTR)
            slam = (
                profile.slam_attack * (1 + slam_bonus / 100) * element_factor * crit_factor
            )
            baseline_slam = profile.slam_attack * base_crit_factor
        else:
            skipped.append("震地")
        if profile.heavy_attack_damage:
            heavy_bonus = damage_bonus + _sum_attr(attributes, HEAVY_ATTR)
            # 重击用重击专属暴击系数（「重击时 x2」在此加倍），不是普通系数。
            heavy = (
                profile.heavy_attack_damage
                * (1 + heavy_bonus / 100)
                * element_factor
                * heavy_crit_factor
            )
            baseline_heavy = profile.heavy_attack_damage * base_crit_factor
        else:
            skipped.append("重击")
        if profile.slam_radial_damage:
            skipped.append("震地范围伤害")

    # ── 第四步：射速 / 多重 / 弹匣 / 装填同样吃紫卡词条 ──
    # ``baseline_dps`` 必须用未修改的基础速度算，否则「提升幅度」的分子分母
    # 都含同一份加成，+100% 射速会显示成 +0%。
    rate_bonus = _sum_attr(attributes, RATE_ATTR)
    multishot_bonus = _sum_attr(attributes, MULTISHOT_ATTR)
    magazine_bonus = _sum_attr(attributes, MAGAZINE_ATTR)
    reload_bonus = _sum_attr(attributes, RELOAD_ATTR)

    base_rate = profile.fire_rate
    fire_rate = base_rate * (1 + rate_bonus / 100) if base_rate else None
    base_multishot = float(profile.multishot or 1)
    multishot = base_multishot * (1 + multishot_bonus / 100)

    duty: float | None = None
    dps: float | None = None
    baseline_dps: float | None = None
    if profile.melee:
        # 近战没有弹匣 / 装填 / 多重：持续 DPS 就是「单次期望 × 攻击速度」，
        # 不乘装填占空比（那会把近战 DPS 算低一个量级）。攻击速度词条有效。
        if fire_rate and fire_rate > 0:
            dps = per_shot * fire_rate
            baseline_dps = baseline_per_shot * base_rate
        else:
            skipped.append("持续 DPS")
    else:
        magazine = (
            profile.magazine_size * (1 + magazine_bonus / 100)
            if profile.magazine_size
            else None
        )
        # 装填速度 +X% 是「装得更快」，时间要除：t' = t / (1 + X%)。
        reload_factor = 1 + reload_bonus / 100
        reload_time = (
            profile.reload_time / reload_factor
            if profile.reload_time is not None and reload_factor > 0
            else None
        )
        if (
            fire_rate
            and fire_rate > 0
            and multishot > 0
            and magazine
            and magazine > 0
            and reload_time is not None
            and reload_time >= 0
        ):
            duty = magazine / (magazine + reload_time * fire_rate)
            dps = per_shot * fire_rate * multishot * duty
            baseline_duty = profile.magazine_size / (
                profile.magazine_size + profile.reload_time * base_rate
            )
            baseline_dps = (
                baseline_per_shot * base_rate * base_multishot * baseline_duty
            )
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
        heavy_crit_factor=heavy_crit_factor,
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
    damage: tuple[tuple[str, float], ...] = ()
    if callable(getter):
        # 解析失败只影响构成条，不该让整张卡崩掉；模型自身已拦 JSON 错误，
        # 这里兜的是脏数据形状（如元素项缺字段）。
        with contextlib.suppress(Exception):
            damage = tuple((item.name, item.damage) for item in getter())

    def value(name: str) -> float | None:
        """按字段名读数值；导出缺列时返回 ``None``（按「无此属性」处理）。"""
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
