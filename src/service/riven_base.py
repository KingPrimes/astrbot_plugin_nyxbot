"""紫卡词条基础数值表（wiki 常量，替代 CDN 的 ``RivenAnalyseTrend``）。

数据来源
--------
* https://wiki.warframe.com/w/Riven_Mods#Base_Values （rank 8 基础值）
* https://warframe.huijiwiki.com/wiki/裂罅MOD （中文词条名与熔接属性）

计算公式（wiki 原文）::

    词条数值 = 基础值 × 倾向 × 布局系数 × 波动系数 [0.9, 1.1]

自 **更新 44.1.3** 起裂罅倾向性被移除，所有武器统一按等效 ``1.2`` 计算，
因此本表存的是**未乘 1.2** 的 rank 8 基础值，由 :func:`compute_range` 统一乘。

表格约定
--------
* 列顺序：步枪 / 霰弹枪 / 手枪 / 曲翼枪械 / 近战；
* ``0`` 表示该武器类型没有这个词条；
* 后坐力基础值是 ``-90``（正属性时结果为负值，即「降低后坐力」），
  与 wiki 的 ``-91.1% ~ -111.4%`` 一致；
* 熔接属性（Riven Splicer）永远不会是负词条，但基础值算法相同。
"""
from __future__ import annotations

from dataclasses import dataclass

#: 当前版本统一的裂罅倾向倍率（更新 44.1.3 移除倾向系统后固定为 1.2）。
DISPOSITION = 1.2

#: 波动系数下限 / 上限（wiki：实际数值在基础值的 90%~110% 之间随机）。
ROLL_MIN = 0.9
ROLL_MAX = 1.1

#: 武器类型（对应 :class:`RivenBase` 的列）。
WEAPON_KINDS: tuple[str, ...] = ("rifle", "shotgun", "pistol", "archwing", "melee")


@dataclass(frozen=True, slots=True)
class RivenBase:
    """一条紫卡词条在五类武器上的基础值。"""

    name: str
    rifle: float = 0.0
    shotgun: float = 0.0
    pistol: float = 0.0
    archwing: float = 0.0
    melee: float = 0.0
    prefix: str = "-"
    suffix: str = "-"
    flat: bool = False
    """平值词条（穿透 m / 攻击范围 m / 连击秒数 / 初始连击 / 格挡角度），展示时不带 %。"""

    spliced: bool = False
    """熔接属性（Riven Splicer），永远为正。"""

    positive_only: bool = False
    negative_only: bool = False

    def value_for(self, kind: str) -> float | None:
        """取某个武器类型的基础值；没有该词条时返回 ``None``。"""
        value = getattr(self, kind, 0.0)
        return value or None


@dataclass(frozen=True, slots=True)
class RivenLayout:
    """正面 / 负面词条数量对应的系数（wiki ``Type of Stats`` 表）。"""

    positive: int
    negative: int
    positive_factor: float
    negative_factor: float | None

    @property
    def label(self) -> str:
        return f"{self.positive}正{self.negative}负"

    def factor(self, is_negative: bool) -> float | None:
        return self.negative_factor if is_negative else self.positive_factor


#: 游戏内只存在这四种布局（2~3 条正面，最多 1 条负面）。
LAYOUTS: tuple[RivenLayout, ...] = (
    RivenLayout(2, 0, 0.99, None),
    RivenLayout(2, 1, 1.2375, -0.495),
    RivenLayout(3, 0, 0.75, None),
    RivenLayout(3, 1, 0.9375, -0.75),
)

LAYOUT_BY_COUNTS: dict[tuple[int, int], RivenLayout] = {
    (layout.positive, layout.negative): layout for layout in LAYOUTS
}


# 词条名, 前缀, 后缀, 步枪, 霰弹枪, 手枪, 曲翼枪械, 近战
_NORMAL: tuple[tuple[str, str, str, float, float, float, float, float], ...] = (
    ("伤害/近战伤害", "Visi", "Ata", 165.0, 164.7, 219.6, 99.9, 164.7),
    ("多重射击", "Sati", "Can", 90.0, 119.7, 119.7, 60.3, 0.0),
    ("冲击伤害", "Magna", "Ton", 119.97, 119.97, 119.97, 90.0, 119.7),
    ("切割伤害", "Sci", "Sus", 119.97, 119.97, 119.97, 90.0, 119.7),
    ("穿刺伤害", "Insi", "Cak", 119.997, 119.997, 119.997, 90.0, 119.997),
    ("冰冻伤害", "Geli", "Do", 90.0, 90.0, 90.0, 119.7, 90.0),
    ("毒素伤害", "Toxi", "Tox", 90.0, 90.0, 90.0, 119.7, 90.0),
    ("电击伤害", "Vexi", "Tio", 90.0, 90.0, 90.0, 119.7, 90.0),
    ("火焰伤害", "Igni", "Pha", 90.0, 90.0, 90.0, 119.7, 90.0),
    ("暴击几率", "Crita", "Cron", 149.99, 90.0, 149.99, 99.9, 180.0),
    ("暴击伤害", "Acri", "Tis", 119.997, 90.0, 90.0, 80.1, 90.0),
    ("触发几率", "Hexa", "Dex", 90.0, 90.0, 90.0, 60.3, 90.0),
    ("触发时间", "Deci", "Des", 99.99, 99.99, 99.99, 99.99, 99.99),
    ("攻击范围", "Locti", "Tor", 0.0, 0.0, 0.0, 0.0, 1.94),
    ("射速/攻击速度", "Croni", "Dra", 60.03, 90.0, 74.7, 60.03, 54.9),
    ("额外连击数几率", "Laci", "Nus", 0.0, 0.0, 0.0, 0.0, 58.77),
    ("几率不获得连击数", "-", "-", 0.0, 0.0, 0.0, 0.0, 104.85),
    ("连击持续时间", "Tempi", "Nem", 0.0, 0.0, 0.0, 0.0, 8.1),
    ("初始连击", "Para", "Um", 0.0, 0.0, 0.0, 0.0, 24.5),
    ("对Corpus伤害", "Manti", "Tron", 45.0, 45.0, 45.0, 45.0, 45.0),
    ("对Grineer伤害", "Argi", "Con", 45.0, 45.0, 45.0, 45.0, 45.0),
    ("对Infested伤害", "Pura", "Ada", 45.0, 45.0, 45.0, 45.0, 45.0),
    ("装填速度", "Feva", "Tak", 49.995, 49.995, 49.995, 99.9, 0.0),
    ("弹药最大值", "Ampi", "Bin", 49.95, 90.0, 90.0, 99.9, 0.0),
    ("弹匣容量", "Arma", "Tin", 49.995, 49.995, 49.995, 60.3, 0.0),
    ("滑行攻击暴击几率", "Pleci", "Nent", 0.0, 0.0, 0.0, 0.0, 120.0),
    ("处决伤害", "Exi", "Cta", 0.0, 0.0, 0.0, 0.0, 119.7),
    ("投射物飞行速度", "Conci", "Nak", 90.0, 90.0, 90.0, 0.0, 0.0),
    ("重击效率", "Forti", "Us", 0.0, 0.0, 0.0, 0.0, 73.44),
    ("穿透", "Lexi", "Nok", 2.7, 2.7, 2.7, 2.7, 0.0),
    ("后坐力", "Zeti", "Mag", -90.0, -90.0, -90.0, -90.0, 0.0),
    ("变焦", "Hera", "Lis", 59.99, 41.994, 80.1, 59.99, 0.0),
)

# 熔接属性：只能由 Riven Splicer 合成，永远是正词条
_SPLICED: tuple[tuple[str, str, str, float, float, float, float, float], ...] = (
    ("弹药效率", "Parci", "Pia", 45.0, 45.0, 45.0, 45.0, 0.0),
    ("爆炸伤害", "Fraga", "Tus", 90.0, 90.0, 90.0, 90.0, 90.0),
    ("腐蚀伤害", "Cori", "Or", 90.0, 90.0, 90.0, 90.0, 90.0),
    ("对Orokin伤害", "Effi", "Tas", 45.0, 45.0, 45.0, 45.0, 45.0),
    ("对炽蛇军伤害", "Exsi", "Llo", 45.0, 45.0, 45.0, 45.0, 45.0),
    ("对科腐者伤害", "Muti", "Gia", 45.0, 45.0, 45.0, 45.0, 45.0),
    ("毒气伤害", "Cali", "Fel", 90.0, 90.0, 90.0, 90.0, 90.0),
    ("重击准备速度", "Veri", "Lus", 0.0, 0.0, 0.0, 0.0, 119.7),
    ("磁力伤害", "Magni", "Bra", 90.0, 90.0, 90.0, 90.0, 90.0),
    ("重击伤害", "Robi", "Ndo", 0.0, 0.0, 0.0, 0.0, 119.7),
    ("格挡角度", "Defi", "So", 0.0, 0.0, 0.0, 0.0, 81.0),
    ("辐射伤害", "Radi", "Lo", 90.0, 90.0, 90.0, 90.0, 90.0),
    ("收起时自动装填", "Auxi", "Rro", 90.0, 90.0, 90.0, 0.0, 0.0),
    ("震地攻击伤害", "Proci", "Lam", 0.0, 0.0, 0.0, 0.0, 119.7),
    ("异常状态伤害", "Plaga", "Mna", 90.0, 90.0, 90.0, 90.0, 90.0),
    ("病毒伤害", "Cari", "Sco", 90.0, 90.0, 90.0, 90.0, 90.0),
    ("弱点伤害", "Eni", "Vo", 225.0, 225.0, 225.0, 225.0, 0.0),
    ("弱点暴击几率", "Exiti", "Eus", 247.5, 247.5, 247.5, 247.5, 0.0),
)

#: 平值词条：卡面就是数字本身（``+3.5`` 穿透），不是百分比。
_FLAT: frozenset[str] = frozenset({
    "穿透", "攻击范围", "连击持续时间", "初始连击", "格挡角度",
})

#: 只会作为正词条出现（wiki 表脚注 ¹）。
_POSITIVE_ONLY: frozenset[str] = frozenset({
    "额外连击数几率", "冰冻伤害", "电击伤害", "火焰伤害", "毒素伤害",
    "穿透", "伤害/近战伤害", "格挡角度",
})

#: 只会作为负词条出现（wiki 表脚注 ³）。
_NEGATIVE_ONLY: frozenset[str] = frozenset({"几率不获得连击数"})


def _build_table() -> dict[str, RivenBase]:
    table: dict[str, RivenBase] = {}
    for rows, spliced in ((_NORMAL, False), (_SPLICED, True)):
        for name, prefix, suffix, *values in rows:
            rifle, shotgun, pistol, archwing, melee = values
            table[name] = RivenBase(
                name=name,
                rifle=rifle,
                shotgun=shotgun,
                pistol=pistol,
                archwing=archwing,
                melee=melee,
                prefix=prefix,
                suffix=suffix,
                flat=name in _FLAT,
                spliced=spliced,
                positive_only=name in _POSITIVE_ONLY,
                negative_only=name in _NEGATIVE_ONLY,
            )
    return table


#: 词条名 → 基础值。共 32 条常规 + 18 条熔接。
BASE_VALUES: dict[str, RivenBase] = _build_table()


#: 整名别名（OCR 展示名 → 正式词条名）。注意：这里只做**整串**匹配，
#: 所以 ``伤害`` 不会把 ``异常状态伤害`` 吞掉。
ALIASES: dict[str, str] = {
    "伤害": "伤害/近战伤害",
    "近战伤害": "伤害/近战伤害",
    "基础伤害": "伤害/近战伤害",
    "在重击时的近战伤害": "重击伤害",
    "重击时的近战伤害": "重击伤害",
    "重击时伤害": "重击伤害",
    "武器后坐力": "后坐力",
    "暴击率": "暴击几率",
    "爆击几率": "暴击几率",
    "触发率": "触发几率",
    "攻击速度": "射速/攻击速度",
    "射速": "射速/攻击速度",
    "投射物速度": "投射物飞行速度",
    "滑行": "滑行攻击暴击几率",
    "滑攻击": "滑行攻击暴击几率",
    "范围": "攻击范围",
    "连击时间": "连击持续时间",
    "额外连击": "额外连击数几率",
}

#: OCR 残句兜底：关键字 → 正式词条名。按顺序匹配，越具体越靠前。
#: 只收录「正式名不是它子串」的情况，避免与最长匹配打架。
_FRAGMENTS: tuple[tuple[str, str], ...] = (
    ("lnfested", "对Infested伤害"),
    ("Infested", "对Infested伤害"),
    ("Grinner", "对Grineer伤害"),
    ("Grineer", "对Grineer伤害"),
    ("Corpus", "对Corpus伤害"),
    ("Orokin", "对Orokin伤害"),
    ("炽蛇军", "对炽蛇军伤害"),
    ("科腐者", "对科腐者伤害"),
    ("重击准备", "重击准备速度"),
    ("重击效率", "重击效率"),
    ("重击伤害", "重击伤害"),
    ("额外连击", "额外连击数几率"),
    ("连击数", "几率不获得连击数"),
    ("滑攻", "滑行攻击暴击几率"),
    ("滑行", "滑行攻击暴击几率"),
    ("暴击几率", "暴击几率"),
    ("暴击率", "暴击几率"),
    ("触发几率", "触发几率"),
    ("触发率", "触发几率"),
    ("攻击速度", "射速/攻击速度"),
    ("射速", "射速/攻击速度"),
    ("投射物", "投射物飞行速度"),
    ("后坐力", "后坐力"),
    ("弹药效率", "弹药效率"),
    ("弹药", "弹药最大值"),
    ("弹匣", "弹匣容量"),
    ("装填速度", "装填速度"),
    ("收起", "收起时自动装填"),
    ("异常状态", "异常状态伤害"),
    ("弱点暴击", "弱点暴击几率"),
    ("弱点", "弱点伤害"),
    ("穿透", "穿透"),
    ("变焦", "变焦"),
    ("多重", "多重射击"),
    ("格挡", "格挡角度"),
    ("震地", "震地攻击伤害"),
    ("处决", "处决伤害"),
    ("连击持续", "连击持续时间"),
    ("初始连击", "初始连击"),
    # 元素 / 物理伤害：OCR 常把「伤害」二字吞掉，只剩前缀
    ("冲击", "冲击伤害"),
    ("切割", "切割伤害"),
    ("穿刺", "穿刺伤害"),
    ("冰冻", "冰冻伤害"),
    ("毒素", "毒素伤害"),
    ("电击", "电击伤害"),
    ("火焰", "火焰伤害"),
    ("爆炸", "爆炸伤害"),
    ("腐蚀", "腐蚀伤害"),
    ("毒气", "毒气伤害"),
    ("磁力", "磁力伤害"),
    ("辐射", "辐射伤害"),
    ("病毒", "病毒伤害"),
)


def lookup(name: str) -> RivenBase | None:
    """按词条名查基础值（精确 → 整名别名 → 最长子串 → OCR 残句）。"""
    key = (name or "").strip()
    if not key:
        return None
    exact = BASE_VALUES.get(key)
    if exact is not None:
        return exact

    alias = ALIASES.get(key)
    if alias is not None:
        return BASE_VALUES[alias]

    # 最长子串：``暴击几率（重击时 x2）`` 命中 ``暴击几率``，
    # 而 ``异常状态伤害`` 会先在上面的精确分支命中，不会被 ``伤害`` 抢走。
    best_name = ""
    for full in BASE_VALUES:
        if full in key and len(full) > len(best_name):
            best_name = full
    if best_name:
        return BASE_VALUES[best_name]

    for fragment, target in _FRAGMENTS:
        if fragment in key:
            return BASE_VALUES[target]
    return None


def normalize(name: str) -> str:
    """返回词条的正式名；查不到时原样返回。"""
    base = lookup(name)
    return base.name if base else name


def compute_range(
    base_value: float | None,
    layout: RivenLayout,
    is_negative: bool,
) -> tuple[float, float]:
    """算一条词条的理论区间。

    ``base_value`` 是 wiki 的 rank 8 基础值（未乘 1.2），返回已乘倾向、
    布局系数与波动系数的 ``(low, high)``，保留 4 位小数，且保证小值在前。

    负词条乘上负系数后 ``low > high``，这里统一成「小值在前」，
    卡片上才是 ``(-78.2% - -64.0%)`` 而不是反过来的双负号。
    """
    if not base_value:
        return 0.0, 0.0
    factor = layout.factor(is_negative)
    if factor is None:
        return 0.0, 0.0

    low = round(ROLL_MIN * base_value * DISPOSITION * factor, 4)
    high = round(ROLL_MAX * base_value * DISPOSITION * factor, 4)
    return (low, high) if low <= high else (high, low)
