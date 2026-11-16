"""Riven Analyse Service / 紫卡分析服务

把 Java ``RivenAttributeCompute`` + ``RivenMatcherUtil`` + ``RivenLookup``
+ ``WeaponSetters`` + ``RivenAnalyseTrendCompute`` 五个类的数学逻辑收敛在此模块。

入口::

    outcome = await RivenAnalyseService.analyse_image(pil_image)
    # outcome.results: list[RivenAnalyseResult]
    # outcome.status:  ok / ocr_failed / no_weapon_name / not_found

设计要点：

* OCR 识别由 :class:`~src.ocr.ocr_service.OcrService` 提供；
* 武器查询走 :class:`~src.model.export.weapons.Weapons`，先精确/包含，
  再拼音、漏字（子序列）与相似度兜底——OCR 掉字/错字是常态；
* 词条基础值走 :mod:`src.service.riven_base` 的 wiki 常量表（32 条常规 +
  18 条熔接 × 5 种武器类型），**不再读 CDN 同步的 RivenAnalyseTrend**；
* 计算公式按 wiki：``基础值 × 1.2 × 布局系数 × [0.9, 1.1]``，其中布局系数
  由正面 / 负面词条数量决定（2正0负 0.99、2正1负 1.2375/-0.495、
  3正0负 0.75、3正1负 0.9375/-0.75）。
"""
from __future__ import annotations

import difflib
import re
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

from pypinyin import Style, lazy_pinyin

from astrbot.api import logger

from ..model.export.weapons import ProductCategory, Weapons
from ..ocr.ocr_service import OcrService
from ..util.search_index import fuzzy_pinyin
from .riven_base import (
    DISPOSITION,
    LAYOUT_BY_COUNTS,
    LAYOUTS,
    RivenBase,
    RivenLayout,
    compute_range,
    lookup as lookup_base,
)
from .riven_estimate import WeaponProfile, profile_from_weapon

if TYPE_CHECKING:
    from PIL import Image as PILImage


# =============================================================================
# 正则表（对应 Java RivenMatcherUtil）
# =============================================================================

# Java 的 `[一-龥]` 用 CJK Unicode 范围。Python re 默认 UNICODE，所以等价。
_IS_CHINES = re.compile(r"[一-龥]*? ?·?&? ?[一-龥]")
_WEAPONS_NAME = re.compile(r"^[一-龥]*?&?·?[一-龥]*$")
_WEAPONS_NAME_EX = re.compile(
    r"^[一-龥]*?&?·?[一-龥] *?[A-Za-z]*?-?[A-Za-z]*?$"
)
_RIVEN_NAME = re.compile(r"[a-zA-Z]*-?$")
_RIVEN_NAME_WITH_HYPHEN = re.compile(r"[a-zA-Z]*-[a-zA-Z]*$")
_IS_ATTRIBUTE = re.compile(
    r".[+-x]?\d+(\.\d+)?%?.?[一-龥]*?.?（?[a-zA-Z]*?.?[一-龥]+$"
)
_ATTRIBUTE_NUM = re.compile(r"[+-]?\d+(\.\d+)?%?")
_IS_DISCRIMINATION = re.compile(
    r"^x\d+(\.\d+)?%?.?[一-龥]*?.?（?[a-zA-Z]*?.?[一-龥]+$"
)
_IS_ATTRIBUTE_NAME = re.compile(
    r"[一-龥]*?（?[a-zA-Z]*?[一-龥]+$"
)
_IS_RIVEN_NAME = re.compile(r"^[一-龥]*? [a-zA-Z]*-[a-zA-Z]*$")
_IS_RIVEN_NAME_EX = re.compile(r"^[一-龥]*? ?[a-zA-Z]*-?$")

# 折行合并用：纯中文短行 / 以数值结尾的行
_CJK_ONLY = re.compile(r"[一-龥·]+")
_VALUE_TAIL = re.compile(r"[%\d]$")
# OCR 会把小数点认成逗号 / 单引号：`+207,7%`、`+135'2%`（同一批图里很常见）
_DECIMAL_MARK = re.compile(r"(?<=\d)[,'’·](?=\d)")


# =============================================================================
# 字符替换 / 词条映射（对应 Java RivenLookup）
# =============================================================================

# OCR 易错字修正
_CHAR_REPLACEMENTS: dict[str, str] = {
    "淞": "凇",
}

# 值为负时反而是正属性的特殊词条（如"后坐力"）
_INVERTED_ATTRIBUTE_KEYWORDS: tuple[str, ...] = ("后坐力",)

# 歧视词条关键字（命中后 attrDiff 走特殊公式）
_DISCRIMINATION_KEYWORDS: tuple[str, ...] = (
    "Infested",
    "Corpus",
    "Grinner",
    "Grineer",
)


# =============================================================================
# Dataclass 结果模型
# =============================================================================

@dataclass
class ResultAttribute:
    """单条紫卡词条的分析结果。"""

    name: str                  # 词条正式名（wiki 常量表里的键）
    attribute_name: str        # 展示用词条名（纯名称）
    attr: float                # OCR 出来的数值（含正负；歧视词条是倍率）
    low: float                 # 计算后最低值
    high: float                # 计算后最高值
    diff: str                  # 与中位数比对后的差异（"+x.x%" / "-x.x%" / "x1.06" 这类）
    discrimination: bool = False  # 歧视词条（卡面是 x1.06 这种倍率，区间/差异同样按倍率）
    flat: bool = False         # 平值词条（穿透 / 攻击范围 / 连击持续时间 / 初始连击 / 格挡角度），不带 %


@dataclass
class RivenAnalyseResult:
    """单把武器的紫卡分析结果。

    同一张紫卡能装在全部同族变体上，且 44.1.3 起倾向统一为 1.2，
    词条部分在所有变体上逐字相同。因此卡片按「一条结果 = 一个变体」
    组织，词条由渲染层从首个变体上提到共享层，只画一次。
    """

    weapon_name: str
    riven_name: str | None
    weapon_type: str
    omega: float
    dot: str
    attributes: list[ResultAttribute] = field(default_factory=list)
    layout: str = ""
    """正面 / 负面词条布局，如 ``3正1负``。"""

    layout_source: str = "count"
    """布局来源：``count``（按词条正负计数）/ ``fit``（按数值反推）。"""

    profile: WeaponProfile | None = None
    """武器基础属性快照（卡片属性区与估算的输入）；离线构造结果时可为 ``None``。"""

    def attribute_signature(self) -> tuple[tuple[str, float, float, float], ...]:
        """词条指纹（名称 + OCR 数值 + 理论区间），用于判定变体之间词条是否一致。

        只有名称与 OCR 数值相同**不代表**区间相同：不同武器类型查的是基础值表
        的不同列（步枪 / 手枪 / 近战…），算出的 ``(low, high)`` 会不同。指纹若
        不含区间，``_group_results`` 会把这些变体合进一组，``_build_card`` 只展示
        首个变体的区间与差异，其余候选的分析结果被静默丢弃。
        """
        return tuple(
            (attr.name, round(attr.attr, 4), round(attr.low, 4), round(attr.high, 4))
            for attr in self.attributes
        )


class AnalyseStatus(StrEnum):
    """分析结果状态（供指令层出不同文案，避免「匹配失败」被说成「没识别到」）。"""

    OK = "ok"
    OCR_FAILED = "ocr_failed"
    NO_WEAPON_NAME = "no_weapon_name"
    NOT_FOUND = "not_found"


@dataclass
class RivenAnalyseOutcome:
    """端到端分析结果 + 失败原因。"""

    results: list[RivenAnalyseResult] = field(default_factory=list)
    query: str | None = None
    """最终用于查询的武器名（OCR 原文，模糊命中时即模糊输入）。"""
    status: AnalyseStatus = AnalyseStatus.OK
    stage: str = ""
    """武器名命中阶段：exact / contains / pinyin / fuzzy，便于日志定位。"""


# =============================================================================
# 解析中间数据
# =============================================================================

@dataclass
class _ParsedAttribute:
    """OCR 阶段解析出的原始词条（未经武器系数计算）。"""

    name: str            # 展示词条名（正式名由 :func:`riven_base.lookup` 解析）
    attribute_name: str  # 展示用词条名（纯名称，不含数值与 OCR 噪声）
    attribute: float     # 数值
    raw: str = ""        # 清洗后的原始行（歧视词条判定仍要看 x0.5 这种前缀）


@dataclass
class _ParsedRiven:
    """OCR 阶段解析出的整张紫卡。

    OCR 会把词条行（如「冲击伤害」）也认成纯中文，若反复覆盖武器名就会
    拿到最后一条词条；因此这里按「出现顺序」保留全部候选，匹配时逐个尝试，
    第一条能对上武器库的胜出。
    """

    weapon_candidates: list[str] = field(default_factory=list)
    riven_name: str | None = None
    attributes: list[_ParsedAttribute] = field(default_factory=list)

    @property
    def weapon_name(self) -> str | None:
        """首个候选（日志 / 兜底展示用）。"""
        return self.weapon_candidates[0] if self.weapon_candidates else None


# =============================================================================
# RivenMatcherUtil 等价函数
# =============================================================================

def _get_chinese(s: str) -> str:
    """提取字符串中的中文连续片段（含 ``·`` / ``&`` 分隔符）。"""
    return "".join(m.group() for m in _IS_CHINES.finditer(s))


def _is_weapons_name(s: str) -> bool:
    s = s.strip()
    return bool(_WEAPONS_NAME_EX.match(s) or _WEAPONS_NAME.match(s))


def _get_riven_name_e(s: str) -> str:
    """提取紫卡英文名。

    ``_RIVEN_NAME`` 只能取到最后一个纯字母片段，``Visi-armatio`` 会被截成
    ``armatio``；带连字符时优先用 ``_RIVEN_NAME_WITH_HYPHEN`` 取全名。
    """
    hyphenated = _RIVEN_NAME_WITH_HYPHEN.search(s)
    if hyphenated:
        return hyphenated.group()
    return "".join(m.group() for m in _RIVEN_NAME.finditer(s))


def _is_attribute(s: str) -> bool:
    return bool(_IS_ATTRIBUTE.match(s))


def _get_attribute_num(s: str) -> float:
    """提取数值（取最后一次匹配，与 Java 行为一致）。"""
    last = 0.0
    for m in _ATTRIBUTE_NUM.finditer(s):
        last = float(m.group().replace("%", "").strip())
    return last


def _is_discrimination(s: str) -> bool:
    """以 ``x`` 开头的属性视为歧视词条（如 ``x1.39 对Grineer 伤害``）。"""
    return bool(_IS_DISCRIMINATION.match(s))


def _get_attribute_name(s: str) -> str:
    return "".join(m.group() for m in _IS_ATTRIBUTE_NAME.finditer(s)).strip()


def _is_inverted_attribute(attribute_name: str) -> bool:
    return any(k in attribute_name for k in _INVERTED_ATTRIBUTE_KEYWORDS)


def _is_negative_attribute(attribute_name: str, value: float) -> bool:
    if _is_inverted_attribute(attribute_name):
        return value > 0
    return value < 0


def _is_riven_name(s: str) -> bool:
    return bool(_IS_RIVEN_NAME.match(s))


def _is_riven_name_ex(s: str) -> bool:
    return _is_riven_name(s) or bool(_IS_RIVEN_NAME_EX.match(s))


# =============================================================================
# 布局判定
# =============================================================================

def _is_negative_attr(attr: _ParsedAttribute) -> bool:
    """判断一条词条是不是负词条。

    * 歧视词条卡面是倍率：``x0.5`` 是减半（诅咒），``x1.06`` 是正词条；
    * 后坐力这类反向词条：数值为正反而是负词条（后坐力变大）。
    """
    if _is_discrimination(attr.raw):
        return attr.attribute < 1
    return _is_negative_attribute(attr.attribute_name, attr.attribute)


def _observed(attr: _ParsedAttribute) -> float:
    """把卡面数值换算到与 ``low/high`` 相同的单位（歧视词条的倍率 → 百分数）。"""
    if _is_discrimination(attr.raw):
        return (attr.attribute - 1) * 100
    return attr.attribute


def _fit_layout(
    pairs: list[tuple[_ParsedAttribute, RivenBase | None]],
    base_layout: RivenLayout,
    kind: str | None,
    *,
    infer_all: bool,
) -> tuple[RivenLayout, str]:
    """按「哪套系数能让实际数值落进区间」修正布局。

    OCR 最常丢的是**负词条整行**（卡面折行后以「）」结尾，正则直接不认），
    于是 3 正 1 负被当成 3 正 0 负，区间小 65%。所以默认只允许「补回一条
    负词条」，不改正面条数——条数是逐行数出来的，比系数反推可靠。
    只有条数本身就落不到任何合法布局（例如只认出 1 条）时，才放开四种布局。
    """
    def hits(layout: RivenLayout) -> int:
        score = 0
        for attr, base in pairs:
            if base is None:
                continue
            low, high = compute_range(
                base.value_for(kind) if kind else None,
                layout,
                _is_negative_attr(attr),
            )
            if low == 0 and high == 0:
                continue
            lo, hi = min(low, high), max(low, high)
            tol = max(0.15, abs(hi) * 0.0005)
            if lo - tol <= _observed(attr) <= hi + tol:
                score += 1
        return score

    base_score = hits(base_layout)
    if infer_all:
        candidates = list(LAYOUTS)
    elif base_layout.negative == 0:
        alt = LAYOUT_BY_COUNTS.get((base_layout.positive, 1))
        candidates = [alt] if alt is not None else []
    else:
        candidates = []

    best_layout, best_score = base_layout, base_score
    for layout in candidates:
        score = hits(layout)
        if score > best_score:
            best_layout, best_score = layout, score
    if best_score > base_score:
        return best_layout, "fit"
    return base_layout, "count"


def _attr_diff(
    name: str,
    attr: float,
    low: float,
    high: float,
) -> str:
    """计算实际值与 (low+high)/2 的差异字符串。

    歧视词条（``x1.06 对Grineer的伤害``）在卡面是倍率、在趋势表里是百分数，
    先统一换算成百分数再比：``(倍率-1)*100``。Java 原版对 ``x < 1`` 分支写成
    ``100-abs*100``，会丢掉负号——``x0.5``（减半，明显是诅咒）反而被算成
    「高于中位」，这里改成与正倍率同一条式子。
    """
    median = (low + high) / 2

    if any(k in name for k in _DISCRIMINATION_KEYWORDS):
        # 卡面是倍率，差异也用倍率表达：实际倍率 - 中位倍率（例：-0.45x）。
        # 百分数形式（-88.1%）对「x1.06」这种读法没有意义，玩家无法换算。
        delta = abs(attr) - (1 + median / 100)
        if round(delta, 2) == 0:
            return "0.00x"
        return f"{delta:+.2f}x"

    i = abs(attr) - abs(median)
    if attr < 0:
        # 负词条「惩罚越轻越好」：|值| 小于中位数是有利，方向要翻过来，
        # 否则 -66.5%（中位 -71.1%）这种好词条会被标成红色负数。
        i = -i
    return _format_diff(median, attr, i)


def _format_diff(median: float, value: float, i: float) -> str:
    """根据差值正负输出 ``+x.x%`` / ``-x.x%`` / ``0.0%``（Java ``getString`` 等价）。

    卡片上留给差异的宽度只有一行，4 位小数（``+4.9045%``）既挤又没意义，
    统一保留 1 位（``+4.9%``）。
    """
    if median == 0:
        return "0.0%"
    v = round((abs(median) - abs(value)) / abs(median) * 100, 1)
    if i > 0:
        return f"+{abs(v)}%"
    if i == 0:
        return "0.0%"
    return f"-{abs(v)}%"


# =============================================================================
# 倾向点（对应 Java RivenTrendEnum.getRivenTrendDot）
# =============================================================================

def _dot_from_omega(omega: float | None) -> str:
    if omega is None:
        return "●○○○○"
    if omega < 0.7:
        return "●○○○○"
    if omega < 0.9:
        return "●●○○○"
    if omega < 1.15:
        return "●●●○○"
    if omega < 1.3:
        return "●●●●○"
    return "●●●●●"


# =============================================================================
# 武器分类 → 基础数值
# =============================================================================

def _weapon_kind(weapon: Weapons) -> str | None:
    """武器分类 → 基础值表的列名（rifle / shotgun / pistol / archwing / melee）。

    守护武器按描述/名称归并到 shotgun / melee / rifle；
    带 ``霰弹枪`` / ``散弹枪`` 描述的武器统一走 shotgun。
    """
    cat = weapon.productCategory
    desc = weapon.description or ""
    name = weapon.name or ""

    if cat == ProductCategory.SENTINEL_WEAPONS.value:
        if "霰弹枪" in desc:
            return "shotgun"
        if "近战" in desc or "分离" in name:
            return "melee"
        return "rifle"

    if "霰弹枪" in desc or "散弹枪" in desc:
        return "shotgun"

    return {
        ProductCategory.PISTOLS.value: "pistol",
        ProductCategory.LONG_GUNS.value: "rifle",
        ProductCategory.MELEE.value: "melee",
        ProductCategory.SPACE_GUNS.value: "archwing",
        ProductCategory.SPACE_MELEE.value: "archwing",
        ProductCategory.SHOTGUNS.value: "shotgun",
        ProductCategory.SPECIAL_ITEMS.value: None,
        ProductCategory.CREW_SHIP_WEAPONS.value: None,
    }.get(cat)


def _select_base(base: RivenBase, kind: str | None) -> float | None:
    """取某条词条在指定武器类型下的基础值。"""
    return base.value_for(kind) if kind else None


def _weapon_type_display(weapon: Weapons) -> str:
    """武器类型展示名（取 ``ProductCategory.display_name``）。"""
    cat = weapon.productCategory
    if not cat:
        return "未知"
    try:
        return ProductCategory(cat).display_name
    except ValueError:
        return cat


# =============================================================================
# 武器名兜底匹配（OCR 漏字 / 错字 / 繁体）
# =============================================================================

WEAPON_MATCH_LIMIT = 4
"""一次分析最多渲染几把候选武器。

同一张紫卡能装在全部变体上（拉特昂 / Prime / 亡魂），而倾向数值按变体不同，
所以精确命中后仍要把同族变体一起给出来；上限 4 防止「双枪」这类关键词
一次刷出几十张卡。
"""

_RATIO_MIN = 0.7
"""字面相似度阈值（4 字名错 1 字 = 0.75，正好卡在线上）。"""

_PINYIN_RATIO_MIN = 0.85
"""拼音相似度阈值（`毒囊双检` / `毒囊双枪` ≈ 0.91）。"""

_SUBSEQ_MIN_LEN = 3
"""少于 3 字不做「漏字」子序列匹配，否则 1~2 字会命中一大片。"""

_PINYIN_CACHE: dict[str, str] = {}


@dataclass(frozen=True)
class _WeaponMatch:
    """武器名匹配结果。"""

    query: str
    rows: list[tuple[str, str]]
    """``(武器名, uniqueName)``，按候选顺序。"""
    stage: str
    """exact / contains / pinyin / fuzzy。"""


def _compact(text: str) -> str:
    """名称比较键：去掉空白与间隔号（``赤毒·布拉玛`` 与 ``赤毒布拉玛`` 等价）。"""
    return re.sub(r"[\s·・]+", "", text or "").lower()


def _pinyin_key(name: str) -> str:
    """名称的拼音键（带模糊音归一化），纯 ASCII 名称返回空串。"""
    cached = _PINYIN_CACHE.get(name)
    if cached is not None:
        return cached
    if not re.search(r"[一-龥]", name):
        _PINYIN_CACHE[name] = ""
        return ""
    syllables = [s for s in lazy_pinyin(name, style=Style.NORMAL, errors="ignore") if s]
    key = fuzzy_pinyin("".join(syllables))
    _PINYIN_CACHE[name] = key
    return key


def _is_subsequence(part: str, whole: str) -> bool:
    """``part`` 是否为 ``whole`` 的子序列（容忍 OCR 漏字，不要求连续）。"""
    it = iter(whole)
    return all(ch in it for ch in part)


def _ratio(left: str, right: str) -> float:
    return difflib.SequenceMatcher(None, left, right).ratio()


def _match_weapon_name(
    candidates: list[str],
    rows: list[tuple[str, str]],
) -> _WeaponMatch | None:
    """按「精确 → 包含 → 拼音 → 模糊」顺序把 OCR 武器名对到武器库。

    每个阶段都先试完所有候选再降级：词条行（``冲击伤害``）也会被认成武器名，
    但真武器名一定排在它前面且能被精确/包含命中，不会被后面的噪声抢走。

    Args:
        candidates: OCR 解析出的武器名候选（按出现顺序）。
        rows: ``(武器名, uniqueName)`` 全量索引。

    Returns:
        命中的 ``_WeaponMatch``；完全对不上返回 ``None``。
    """
    prepared = [(name, uid, _compact(name)) for name, uid in rows if name]
    queries = [
        (cand, compact, _pinyin_key(cand))
        for cand in candidates
        if (compact := _compact(cand))
    ]

    def same_pinyin(pinyin: str) -> list[tuple[str, str]]:
        """拼音命中 + 同族变体（``豪豬`` → 豪猪 / 豪猪 Prime）。"""
        if len(pinyin) < 4:
            return []
        return _rank([
            (n, u) for n, u, _ in prepared
            if (pk := _pinyin_key(n)) and (pk == pinyin or pinyin in pk)
        ])

    # 精确 / 包含：命中后带上同族变体
    for cand, key, _ in queries:
        exact = [(n, u) for n, u, c in prepared if c == key]
        near = _rank([(n, u) for n, u, c in prepared if c != key and key in c])
        if exact or near:
            hit = exact + near
            return _WeaponMatch(
                cand, hit[:WEAPON_MATCH_LIMIT], "exact" if exact else "contains"
            )

    # 拼音：繁体 / 同音错字
    for cand, _, pinyin in queries:
        hit = same_pinyin(pinyin)
        if hit:
            return _WeaponMatch(cand, hit[:WEAPON_MATCH_LIMIT], "pinyin")

    # 模糊：漏字（子序列）/ 错字（字面或拼音相似度）
    scored: dict[str, tuple[float, str, str]] = {}
    for _, key, pinyin in queries:
        for name, uid, compact in prepared:
            raw_score = _ratio(key, compact)
            name_pinyin = _pinyin_key(name)
            pinyin_score = _ratio(pinyin, name_pinyin) if pinyin and name_pinyin else 0.0
            missing_char = len(key) >= _SUBSEQ_MIN_LEN and _is_subsequence(key, compact)
            if not (
                raw_score >= _RATIO_MIN
                or pinyin_score >= _PINYIN_RATIO_MIN
                or missing_char
            ):
                continue
            score = max(raw_score, pinyin_score, _RATIO_MIN if missing_char else 0.0)
            prev = scored.get(uid)
            if prev is None or score > prev[0]:
                scored[uid] = (score, name, uid)
    if not scored:
        return None
    ranked = sorted(scored.values(), key=lambda x: (-x[0], len(x[1]), x[1]))
    return _WeaponMatch(
        queries[0][0] if queries else candidates[0],
        [(name, uid) for _, name, uid in ranked[:WEAPON_MATCH_LIMIT]],
        "fuzzy",
    )


def _rank(rows: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """候选排序：名称短的优先（``阿利乌双枪`` 先于 ``阿利乌双枪 Prime``）。"""
    return sorted(rows, key=lambda row: (len(row[0]), row[0]))


# =============================================================================
# RivenAnalyseService
# =============================================================================

class RivenAnalyseService:
    """紫卡分析服务（OCR → 解析 → 计算 → 结果）。

    词条基础值来自 :mod:`src.service.riven_base` 的 wiki 常量表，纯内存查表，
    不再依赖 CDN 同步的 ``RivenAnalyseTrend``。
    """

    @classmethod
    async def analyse_image(cls, image: PILImage.Image) -> RivenAnalyseOutcome:
        """端到端分析入口。

        Args:
            image: 紫卡截图（PIL Image）。

        Returns:
            ``RivenAnalyseOutcome``：成功时带按候选顺序排好的结果，失败时带
            具体原因（OCR 失败 / 没识别到武器名 / 识别到但对不上武器库），
            供指令层出对应文案——不能把「匹配失败」说成「没识别到」。
        """
        total_t0 = time.perf_counter()

        # OCR 识别
        ocr_t0 = time.perf_counter()
        ocr = OcrService()
        try:
            texts = await ocr.recognize_text_only(image)
        except Exception as e:
            logger.error(f"PaddleOCR 识别失败: {e}")
            return RivenAnalyseOutcome(status=AnalyseStatus.OCR_FAILED)
        logger.debug(
            "OCR 耗时 %.2fs, 识别到 %d 行文本",
            time.perf_counter() - ocr_t0, len(texts),
        )

        logger.debug(f"紫卡 OCR 文字识别结果: {texts}")
        merged = cls._merge_wrapped_lines(texts)
        if merged != texts:
            logger.debug(f"折行合并后: {merged}")
        parsed = cls._parse_ocr_lines(merged)
        logger.debug(
            "紫卡解析: weapon=%s candidates=%s riven=%s attrs=%s",
            parsed.weapon_name,
            parsed.weapon_candidates,
            parsed.riven_name,
            [(a.name, a.attribute_name, a.attribute) for a in parsed.attributes],
        )

        if not parsed.weapon_candidates:
            return RivenAnalyseOutcome(status=AnalyseStatus.NO_WEAPON_NAME)

        # 武器名解析：精确 → 包含 → 拼音 → 模糊（漏字/错字/繁体）
        weapon_t0 = time.perf_counter()
        candidates = [
            cls._apply_char_replace(name) for name in parsed.weapon_candidates
        ]
        rows = await Weapons.all().values_list("name", "uniqueName")
        match = _match_weapon_name(
            candidates, [(name, uid) for name, uid in rows if name]
        )
        logger.debug(
            "武器匹配耗时 %.2fs, 候选=%s, 命中阶段=%s, 匹配到 %d 把",
            time.perf_counter() - weapon_t0,
            candidates,
            match.stage if match else "-",
            len(match.rows) if match else 0,
        )

        if match is None:
            logger.info(
                "紫卡分析：识别到武器名但无匹配 (候选=%r)", candidates
            )
            return RivenAnalyseOutcome(
                query=parsed.weapon_name, status=AnalyseStatus.NOT_FOUND
            )

        # 计算各武器结果（trend 已缓存到内存，纯 CPU 计算无需 IO）
        build_t0 = time.perf_counter()
        order = {uid: index for index, (_, uid) in enumerate(match.rows)}
        weapons = await Weapons.filter(
            uniqueName__in=[uid for _, uid in match.rows]
        ).all()
        weapons.sort(key=lambda w: order.get(w.uniqueName, len(order)))
        results = [cls._build_result(w, parsed) for w in weapons]
        logger.debug(
            "词条计算耗时 %.2fs (%d 把武器)",
            time.perf_counter() - build_t0, len(weapons),
        )

        logger.debug(
            "紫卡分析总耗时 %.2fs (OCR + 解析 + 查询 + 计算)",
            time.perf_counter() - total_t0,
        )
        return RivenAnalyseOutcome(
            results=results,
            query=match.query,
            status=AnalyseStatus.OK,
            stage=match.stage,
        )

    # ------------------------------------------------------------------
    # OCR 行解析
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_char_replace(s: str) -> str:
        for src, dst in _CHAR_REPLACEMENTS.items():
            s = s.replace(src, dst)
        return s

    @classmethod
    def _parse_ocr_lines(cls, lines: list[str]) -> _ParsedRiven:
        """复刻 Java ``RivenAttributeCompute.getRiven``。"""
        parsed = _ParsedRiven()
        raw_attrs: list[str] = []

        for original in lines:
            if not original or len(original) < 3:
                continue
            s = original
            ext = _get_riven_name_e(s) if _is_riven_name_ex(s) else ""

            # 武器名：只收集候选，是否命中武器库交给 _match_weapon_name 判断
            if _is_weapons_name(s):
                if "&" in s:
                    i = s.index("&")
                    if i > 0 and i + 1 < len(s):
                        prev_ch = s[i - 1]
                        next_ch = s[i + 1]
                        if prev_ch != " " and next_ch != " ":
                            s = s.replace("&", " & ")
                name = _get_chinese(s)
                if name and name not in parsed.weapon_candidates:
                    parsed.weapon_candidates.append(name)

            # 紫卡名（武器行带的 / 单独的英文行）
            if ext:
                cls._append_riven_name(parsed, ext)

            # 属性词条
            if _is_attribute(s):
                cleaned = _DECIMAL_MARK.sub(".", s).replace(" ", "").strip()
                raw_attrs.append(cleaned.replace("入", ""))

        # 逐行提取词条；正负与布局统一交给 _build_result 判定
        for raw in raw_attrs:
            # attribute_name 是卡片左侧的展示名，只留词条本身；数值由 low/high 表达
            display = _get_attribute_name(raw)
            if "射速" in raw:
                display = display + "（效果加倍）"
            elif "暴击几率" in raw and "重击" in raw:
                display = "暴击几率（重击时 x2）"
            elif "滑行攻击" in raw or "滑攻击" in raw:
                display = "滑行攻击暴击几率"

            parsed.attributes.append(
                _ParsedAttribute(
                    name=display,
                    attribute_name=display,
                    attribute=_get_attribute_num(raw),
                    raw=raw,
                )
            )

        return parsed

    @staticmethod
    def _append_riven_name(parsed: _ParsedRiven, ext: str) -> None:
        """拼接紫卡英文名（同一名字可能被 OCR 拆成两行）。"""
        current = parsed.riven_name or ""
        if not ext or ext in current:
            return
        parsed.riven_name = current + ext

    @classmethod
    def _merge_wrapped_lines(cls, lines: list[str]) -> list[str]:
        """把被卡面折行拆开的词条拼回去。

        紫卡卡面窄，长词条会换行，OCR 于是给出两行：``-61.9%`` + ``重击效率``、
        ``+87.1%在重击时的近`` + ``战伤害``。不拼回去，负词条会被整条丢掉，
        布局判定随之失效，系数从 1.2375 掉到 0.75——数值全错却不报错。

        判定：上一行是「值结尾 / 值+半截词条」，且其词条名查不到基础值，
        下一行是 2~6 个纯中文字，拼接后能成为合法词条。
        """
        merged: list[str] = []
        for line in lines:
            text = line.strip()
            prev = merged[-1] if merged else ""
            tail_is_value = bool(_VALUE_TAIL.search(prev))
            if (
                prev
                and _CJK_ONLY.fullmatch(text)
                and len(text) <= 6
                and (tail_is_value or _is_attribute(prev))
                and lookup_base(_get_attribute_name(prev)) is None
                and _is_attribute(prev + text)
            ):
                merged[-1] = prev + text
                continue
            merged.append(line)
        return merged

    # ------------------------------------------------------------------
    # 单把武器结果
    # ------------------------------------------------------------------

    @classmethod
    def _build_result(
        cls, weapon: Weapons, parsed: _ParsedRiven
    ) -> RivenAnalyseResult:
        kind = _weapon_kind(weapon)
        pairs = [(attr, lookup_base(attr.name)) for attr in parsed.attributes]

        negative_count = sum(1 for attr, _ in pairs if _is_negative_attr(attr))
        positive_count = len(pairs) - negative_count

        # 布局先按「正负条数」定，再用实际数值校验（OCR 漏掉负词条时纠正）
        counted = LAYOUT_BY_COUNTS.get(
            (min(positive_count, 3), 1 if negative_count else 0)
        )
        base_layout = counted or LAYOUTS[-1]
        layout, layout_source = _fit_layout(
            pairs, base_layout, kind, infer_all=counted is None
        )

        attrs: list[ResultAttribute] = []
        for attr, base in pairs:
            base_value = _select_base(base, kind) if base is not None else None
            is_neg = _is_negative_attr(attr)
            low, high = compute_range(base_value, layout, is_neg)

            attrs.append(
                ResultAttribute(
                    name=base.name if base is not None else attr.name,
                    attribute_name=attr.attribute_name,
                    attr=attr.attribute,
                    low=low,
                    high=high,
                    diff=_attr_diff(
                        base.name if base is not None else attr.name,
                        attr.attribute,
                        low,
                        high,
                    ),
                    discrimination=_is_discrimination(attr.raw),
                    flat=base.flat if base is not None else False,
                )
            )

        if layout_source == "fit":
            logger.info(
                "紫卡分析：按数值反推布局 %s（原计数 %d 正 %d 负）",
                layout.label, positive_count, negative_count,
            )

        return RivenAnalyseResult(
            weapon_name=weapon.name or "",
            riven_name=parsed.riven_name,
            weapon_type=_weapon_type_display(weapon),
            omega=DISPOSITION,
            dot=_dot_from_omega(DISPOSITION),
            attributes=attrs,
            layout=layout.label,
            layout_source=layout_source,
            profile=profile_from_weapon(
                weapon,
                melee=weapon.productCategory
                in (ProductCategory.MELEE.value, ProductCategory.SPACE_MELEE.value),
            ),
        )
