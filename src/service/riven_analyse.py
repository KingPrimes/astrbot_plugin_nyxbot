"""Riven Analyse Service / 紫卡分析服务

把 Java ``RivenAttributeCompute`` + ``RivenMatcherUtil`` + ``RivenLookup``
+ ``WeaponSetters`` + ``RivenAnalyseTrendCompute`` 五个类的数学逻辑收敛在此模块。

入口::

    results = await RivenAnalyseService.analyse_image(pil_image)
    # results: list[RivenAnalyseResult]

设计要点：

* OCR 识别由 :class:`~src.ocr.ocr_service.OcrService` 提供；
* 武器查询走 :class:`~src.model.export.weapons.Weapons` 模糊匹配；
* 词条系数走 :class:`~src.model.riven_analyse_trend.RivenAnalyseTrend`；
* 计算公式按词条数（2 / 3 / 4）+ 是否携带负属性 + 当前词条是否为负属性
  乘以不同修正系数（参考 Java 注释 0.99 / 1.2375 / 0.75 / 0.9375 / -0.495 / -0.75）。
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from astrbot.api import logger

from ..model.export.weapons import ProductCategory, Weapons
from ..model.riven_analyse_trend import RivenAnalyseTrend
from ..ocr.ocr_service import OcrService

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


# =============================================================================
# 字符替换 / 词条映射（对应 Java RivenLookup）
# =============================================================================

# OCR 易错字修正
_CHAR_REPLACEMENTS: dict[str, str] = {
    "淞": "凇",
}

# 词条名 → 用于查 RivenAnalyseTrend.name 的目标关键字（保持插入顺序）
_CHAR_ANALYSE: dict[str, str] = {
    "射速": "射速/攻击速度",
    "攻击速度": "射速/攻击速度",
    "武器后坐力": "后坐力",
    "Infested": "对Infested伤害",
    "lnfested": "对Infested伤害",
    "Corpus": "对Corpus伤害",
    "Grinner": "对Grineer伤害",
    "Grineer": "对Grineer伤害",
    "滑行": "滑行攻击暴击几率",
    "暴击几率": "暴击几率",
    "暴击伤害": "暴击伤害",
    "秒连击持续时间": "连击持续时间",
    "连击数": "几率不获得连击数",
    "冰冻": "冰冻伤害",
    "毒素": "毒素伤害",
    "电击": "电击伤害",
    "火焰": "火焰伤害",
    "冲击": "冲击伤害",
    "切割": "切割伤害",
    "穿刺": "穿刺伤害",
    "投射物": "投射物飞行速度",
    "后坐力": "后坐力",
    "伤害": "伤害/近战伤害",
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

    name: str                  # 用于查 RivenAnalyseTrend 的归一化名称
    attribute_name: str        # 原文显示名称
    attr: float                # OCR 出来的数值（含正负）
    low: float                 # 计算后最低值
    high: float                # 计算后最高值
    diff: str                  # 与中位数比对后的差异（"+x.x%" / "-x.x%" / "0.0%"）


@dataclass
class RivenAnalyseResult:
    """单把武器的紫卡分析结果。"""

    weapon_name: str
    riven_name: str | None
    weapon_type: str
    omega: float
    dot: str
    attributes: list[ResultAttribute] = field(default_factory=list)


# =============================================================================
# 解析中间数据
# =============================================================================

@dataclass
class _ParsedAttribute:
    """OCR 阶段解析出的原始词条（未经武器系数计算）。"""

    name: str            # 用于查 RivenAnalyseTrend 的名字
    attribute_name: str  # 原文 / 展示用
    attribute: float     # 数值
    nag: bool            # 整张紫卡是否携带负属性


@dataclass
class _ParsedRiven:
    """OCR 阶段解析出的整张紫卡。"""

    weapon_name: str | None = None
    riven_name: str | None = None
    attributes: list[_ParsedAttribute] = field(default_factory=list)


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
# 数学公式（对应 Java RivenAnalyseTrendCompute）
# =============================================================================

def _round4(v: float) -> float:
    """保留 4 位小数（对应 Java ``DoubleUtils.formatDouble4``）。"""
    return round(v, 4)


def _compute_low_high(
    base_val: float,
    pro: float,
    attr_count: int,
    nag: bool,
    is_neg: bool,
) -> tuple[float, float]:
    """计算单条词条的最低/最高数值。

    公式 (Java 注释)::

                       正面修正系数    负面修正系数
        2 正             0.99            0
        2 正 1 负        1.2375          -0.495
        3 正             0.75            0
        3 正 1 负        0.9375          -0.75

    返回值 ``(low, high)``，浮动系数 0.9 / 1.1，皆保留 4 位小数。
    """
    factor: float
    if attr_count == 2:
        factor = 0.99
    elif attr_count == 3:
        factor = (-0.495 if is_neg else 1.2375) if nag else 0.75
    elif attr_count == 4:
        factor = -0.75 if is_neg else 0.9375
    else:
        return 0.0, 0.0

    low = _round4(0.9 * base_val * pro * factor)
    high = _round4(1.1 * base_val * pro * factor)
    return low, high


def _attr_diff(
    name: str,
    attr: float,
    low: float,
    high: float,
) -> str:
    """计算实际值与 (low+high)/2 的差异字符串。

    歧视词条采用 Java ``getAttributeDiscriminationDiff`` 公式：
    abs(attr) > 1 → ``(abs-1)*100``，否则 ``100-abs*100``。
    """
    median = (low + high) / 2

    if any(k in name for k in _DISCRIMINATION_KEYWORDS):
        abs_value = abs(attr)
        abs_value = (abs_value - 1) * 100 if abs_value > 1 else 100 - abs_value * 100
        i = abs_value - abs(median)
        return _format_diff(median, abs_value, i)

    i = abs(attr) - abs(median)
    return _format_diff(median, attr, i)


def _format_diff(median: float, value: float, i: float) -> str:
    """根据差值正负输出 ``+x%`` / ``-x%`` / ``0.0%``（Java ``getString`` 等价）。"""
    if median == 0:
        return "0.0%"
    v = _round4((abs(median) - abs(value)) / abs(median) * 100)
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

def _select_base(trend: RivenAnalyseTrend, weapon: Weapons) -> float | None:
    """根据武器分类选择 ``RivenAnalyseTrend`` 中的基础数值。

    守护武器按描述/名称归并到 Shotgun/Melee/LongGun。
    带 ``霰弹枪`` / ``散弹枪`` 描述的武器统一走 shotgun。
    """
    cat = weapon.productCategory
    desc = weapon.description or ""
    name = weapon.name or ""

    if cat == ProductCategory.SENTINEL_WEAPONS.value:
        if "霰弹枪" in desc:
            return trend.shotgun
        if "近战" in desc or "分离" in name:
            return trend.melle
        return trend.rifle

    if "霰弹枪" in desc or "散弹枪" in desc:
        return trend.shotgun

    return {
        ProductCategory.PISTOLS.value: trend.pistol,
        ProductCategory.LONG_GUNS.value: trend.rifle,
        ProductCategory.MELEE.value: trend.melle,
        ProductCategory.SPACE_GUNS.value: trend.archwing,
        ProductCategory.SPACE_MELEE.value: trend.archwing,
        ProductCategory.SHOTGUNS.value: trend.shotgun,
        ProductCategory.SPECIAL_ITEMS.value: None,
        ProductCategory.CREW_SHIP_WEAPONS.value: None,
    }.get(cat)


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
# RivenAnalyseService
# =============================================================================

class RivenAnalyseService:
    """紫卡分析服务（OCR → 解析 → 计算 → 结果）。

    RivenAnalyseTrend 表仅 ~50-60 行，一次性预加载到 :attr:`_trend_cache`
    避免 :meth:`_lookup_trend` 每次查 DB 的 N+1 问题。
    """

    _trend_cache: dict[str, RivenAnalyseTrend] = {}
    _cache_loaded: bool = False

    @classmethod
    async def _ensure_trend_cache(cls) -> None:
        """预加载全部 RivenAnalyseTrend 到内存 dict（仅首次调用访问 DB）。"""
        if cls._cache_loaded:
            return
        t0 = time.perf_counter()
        all_trends = await RivenAnalyseTrend.all()
        cls._trend_cache = {t.name: t for t in all_trends if t.name}
        cls._cache_loaded = True
        logger.debug(
            "趋势缓存预加载完成: %d 条, 耗时 %.2fs",
            len(cls._trend_cache), time.perf_counter() - t0,
        )

    @classmethod
    async def analyse_image(
        cls, image: PILImage.Image
    ) -> list[RivenAnalyseResult]:
        """端到端分析入口。

        Args:
            image: 紫卡截图（PIL Image）。

        Returns:
            按候选武器顺序返回的分析结果列表，OCR 未识别到武器名时返回空列表。
        """
        total_t0 = time.perf_counter()

        # 预加载趋势数据（仅首次触及 DB）
        await cls._ensure_trend_cache()

        # OCR 识别
        ocr_t0 = time.perf_counter()
        ocr = OcrService()
        try:
            texts = await ocr.recognize_text_only(image)
        except Exception as e:
            logger.error(f"PaddleOCR 识别失败: {e}")
            return []
        logger.debug(
            "OCR 耗时 %.2fs, 识别到 %d 行文本",
            time.perf_counter() - ocr_t0, len(texts),
        )

        logger.debug(f"紫卡 OCR 文字识别结果: {texts}")
        parsed = cls._parse_ocr_lines(texts)
        logger.debug(
            "紫卡解析: weapon=%s riven=%s attrs=%s",
            parsed.weapon_name,
            parsed.riven_name,
            [(a.name, a.attribute_name, a.attribute) for a in parsed.attributes],
        )

        if not parsed.weapon_name:
            return []

        # 武器查询
        weapon_t0 = time.perf_counter()
        fixed = cls._apply_char_replace(parsed.weapon_name)
        weapons = await Weapons.filter(name__icontains=fixed).all()
        logger.debug(
            "武器查询耗时 %.2fs, 匹配到 %d 把武器",
            time.perf_counter() - weapon_t0, len(weapons),
        )

        if not weapons:
            logger.info(f"紫卡分析：未匹配到武器 (查询关键字={fixed!r})")
            return []

        # 计算各武器结果（trend 已缓存到内存，纯 CPU 计算无需 IO）
        build_t0 = time.perf_counter()
        results = [cls._build_result(w, parsed) for w in weapons]
        logger.debug(
            "词条计算耗时 %.2fs (%d 把武器)",
            time.perf_counter() - build_t0, len(weapons),
        )

        logger.debug(
            "紫卡分析总耗时 %.2fs (OCR + 解析 + 查询 + 计算)",
            time.perf_counter() - total_t0,
        )
        return list(results)

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

            # 武器名
            if _is_weapons_name(s):
                if "&" in s:
                    i = s.index("&")
                    if i > 0 and i + 1 < len(s):
                        prev_ch = s[i - 1]
                        next_ch = s[i + 1]
                        if prev_ch != " " and next_ch != " ":
                            s = s.replace("&", " & ")
                parsed.weapon_name = _get_chinese(s)
                if _is_riven_name_ex(s):
                    parsed.riven_name = _get_riven_name_e(s)

            # 紫卡名（单独的英文行）
            if _is_riven_name_ex(s):
                ext = _get_riven_name_e(s)
                if parsed.riven_name is None:
                    parsed.riven_name = ext
                elif parsed.riven_name != ext:
                    parsed.riven_name = parsed.riven_name + ext

            # 属性词条
            if _is_attribute(s):
                cleaned = s.replace(" ", "").strip().replace("入", "")
                raw_attrs.append(cleaned)

        # 判定整张紫卡是否携带负属性
        nag = False
        if len(raw_attrs) >= 3:
            last = raw_attrs[-1]
            if _get_attribute_num(last) < 0 or _is_discrimination(last):
                nag = True

        for raw in raw_attrs:
            if "射速" in raw:
                attribute_name = raw + " 效果加倍）"
                name = _get_attribute_name(raw) + " 效果加倍）"
            elif "暴击几率（" in raw or "重击" in raw:
                # Java: substring(0, raw.contains("率") ? raw.indexOf("率")+1 : raw.length()) + "(重击时 x2)"
                base = raw[: raw.index("率") + 1] if "率" in raw else raw
                attribute_name = base + "(重击时 x2)"
                name = "暴击几率（重击时 x2）"
            elif "滑行攻击" in raw:
                attribute_name = re.sub(r"滑.*", "滑行攻击暴击几率", raw)
                name = "滑行攻击暴击几率"
            else:
                attribute_name = raw
                name = _get_attribute_name(raw)

            parsed.attributes.append(
                _ParsedAttribute(
                    name=name,
                    attribute_name=attribute_name,
                    attribute=_get_attribute_num(raw),
                    nag=nag,
                )
            )

        return parsed

    # ------------------------------------------------------------------
    # 单把武器结果
    # ------------------------------------------------------------------

    @classmethod
    def _build_result(
        cls, weapon: Weapons, parsed: _ParsedRiven
    ) -> RivenAnalyseResult:
        omega = weapon.omegaAttenuation or 0.0
        attrs: list[ResultAttribute] = []
        count = len(parsed.attributes)

        for idx, attr in enumerate(parsed.attributes):
            trend = cls._lookup_trend(attr.name)
            base_val = _select_base(trend, weapon) if trend is not None else None

            if idx >= 2:
                is_neg = (
                    _is_discrimination(attr.attribute_name)
                    or _is_negative_attribute(attr.attribute_name, attr.attribute)
                )
            else:
                is_neg = _is_negative_attribute(attr.attribute_name, attr.attribute)

            if base_val is None or omega <= 0:
                low, high = 0.0, 0.0
            else:
                low, high = _compute_low_high(
                    base_val, omega, count, attr.nag, is_neg
                )

            attrs.append(
                ResultAttribute(
                    name=attr.name,
                    attribute_name=attr.attribute_name,
                    attr=attr.attribute,
                    low=low,
                    high=high,
                    diff=_attr_diff(attr.name, attr.attribute, low, high),
                )
            )

        return RivenAnalyseResult(
            weapon_name=weapon.name or "",
            riven_name=parsed.riven_name,
            weapon_type=_weapon_type_display(weapon),
            omega=omega,
            dot=_dot_from_omega(omega),
            attributes=attrs,
        )

    # ------------------------------------------------------------------
    # RivenAnalyseTrend 查找 (内存缓存)
    # ------------------------------------------------------------------

    @classmethod
    def _lookup_trend(cls, analyse_name: str) -> RivenAnalyseTrend | None:
        """纯内存查找 RivenAnalyseTrend（仿 Java ``RivenLookup.findRivenTrendByAnalyseName``）。

        调用前需确保 ``_ensure_trend_cache()`` 已执行。
        """
        for keyword, target in _CHAR_ANALYSE.items():
            if keyword in analyse_name:
                trend = cls._trend_cache.get(target)
                if trend is not None:
                    return trend
        return cls._trend_cache.get(analyse_name)
