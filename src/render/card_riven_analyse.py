"""紫卡分析卡片渲染器

版式（设计文档 ``plans/riven_analyse_card_design_2026-11-16.md``）：

=========== ==========================================================
区          内容
=========== ==========================================================
A 页头      紫卡名（30px）+ 系属 / 变体数 / 词条通用；右侧倾向、段位、布局
B 词条      共享层，每条两行（名称 + 本卡值 / 区间 + 差异），全卡只画一次
C 区头      「武器变体」+「差异以 X 为基准」
D 变体卡    身份 → 核心属性 → 次要属性串（估算接入后追加构成与估算）
E 注脚      口径声明 + 未计项
=========== ==========================================================

三条硬约束：

1. **词条是共享输入，必须画在变体之上**。44.1.3 起裂罅倾向统一 1.2，
   同一张紫卡装在同系所有变体上词条数值完全一致；下沉到每张变体卡
   就等于把同一组数字画 N 遍。
2. **4 个变体不横排**，走 2×2 网格。横排 4 列每列只剩 150px，属性名放
   不下就必然缩字号，会把刚修好的字号问题推回去。
3. **属性行按 0 值规则动态绘制**：全列为 0 整行不画；部分为 0 保留该行、
   空格填浅色 ``—`` 维持对齐；单变体为 0 直接不画。

配色语义：红绿只用于词条差异（有明确优劣方向），武器属性与估算差值
一律金色——装填慢、射速低未必是缺点，用红绿会误导。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..service.riven_estimate import (
    DAMAGE_ATTR,
    build_elements,
    build_estimate,
    element_hints,
)
from . import card_frame as frame
from . import components as C
from .card_size import CardSpec, CustomBlock, measure_card_size
from .design import (
    FONT,
    MAX_WIDTH,
    MIN_WIDTH,
    PAD,
    RADIUS,
    RGB,
    SPACE,
    font,
    font_px,
)
from .theme import current_theme

if TYPE_CHECKING:
    from PIL import Image

    from ..service.riven_analyse import RivenAnalyseResult
    from ..service.riven_estimate import ElementShare, RivenEstimate, WeaponProfile
    from .card_renderer import CardRenderer

# ---------------------------------------------------------------- 版式常量

#: 变体列间距（§2.4）。
_GAP = 14
#: 变体卡内边距（§2.4：16 → 24）。
_CARD_PAD = SPACE["xl"]
#: 区块小标题字号（13 + 字距 0.12em）。
_LABEL_SIZE = 13
_LABEL_TRACKING = 1.6
#: 小标题行高（13px 字的 descent 留 2px）。
_LABEL_H = _LABEL_SIZE + 2
#: 属性行高（§2.4：20 → 30）。
_ATTR_ROW_H = 30
#: 差异另起一行时额外占用的高度（3 列窄卡）。
_DIFF_LINE_H = 16
#: 属性行字号（§2.3：16 → 19）。
_STAT_SIZE = 19
#: 次要属性串字号。
_SECONDARY_SIZE = 15
#: 构成条高度。
_BAR_H = 10
#: 图例字号。
_LEGEND_SIZE = 15
#: 图例色块边长（色块承担颜色语义，文字保持可读的中性色）。
_SWATCH = 8
#: 估算的乘数分解 / DPS 副行字号。
_DECOMP_SIZE = 14
#: 变体身份第二行（类型 · 段位）字号。
_META_SIZE = 16
#: 属性一致时的退化提示字号。
_HINT_SIZE = 15
#: 注脚字号。
_FOOTNOTE_SIZE = 14
#: 每列变体卡宽度（§5）。
_COLUMN_WIDTH = {1: 640, 2: 330, 3: 216}

#: 变体徽标：这些词是变体标识，永不截断（区分变体靠的就是它们）。
_BADGES: tuple[str, ...] = ("Prime", "亡魂", "赤毒", "破坏者", "圣洁", "棱晶", "亡者")

#: 注脚口径（§4.5，必须在卡片上出现，不可省略）。
_DISCLAIMER = "估算为面板等效：未计护甲、元素克制与触发伤害；数值为 0 的属性不绘制。"


# ---------------------------------------------------------------- 文案模型


@dataclass(frozen=True)
class _AttrRow:
    """一条共享词条的绘制文案。

    第一行是「词条名 + 本张紫卡的实际数值」，第二行是「理论区间 + 与中位数的差异」：
    玩家最关心的是自己这张卡到底出了多少，只给区间和差异等于看不到原值。
    """

    name: str
    value: str
    span: str
    diff: str
    color: RGB
    known: bool


@dataclass(frozen=True)
class _StatRow:
    """变体卡里的一行武器属性。"""

    label: str
    value: str
    diff: str
    missing: bool


@dataclass
class _Variant:
    """一张变体卡的绘制文案。"""

    name: str
    badge: str
    meta: str
    stats: list[_StatRow] = field(default_factory=list)
    secondary: str = ""
    secondary_lines: list[str] = field(default_factory=list)
    segments: list[ElementShare] = field(default_factory=list)
    """构成条分段（伤害类型 + 数值 + 来源）。"""
    legend_lines: list[list[tuple[str, RGB]]] = field(default_factory=list)
    """图例，已按宽度折行。"""
    hints: list[str] = field(default_factory=list)
    """复合元素组合提示。"""
    estimate: RivenEstimate | None = None
    """紫卡加成后的估算（§4.2）。"""
    show_diff: bool = True
    """本卡是否展示与基准的差异。"""
    stack_diff: bool = False
    """差异另起一行（列太窄，三段并排会把属性名截断）。"""
    same: bool = False
    """与基准变体属性完全一致——D 区退化为一行提示。"""


@dataclass(frozen=True)
class _Scale:
    """按列数决定的字号规格（§5）。"""

    columns: int
    card_w: int
    name_size: int
    stat_size: int
    diff_size: int
    estimate_size: int


@dataclass
class _Card:
    """一张紫卡卡的绘制文案。"""

    riven: str
    subtitle: str
    info: tuple[str, str]
    attrs: list[_AttrRow]
    variants: list[_Variant]
    scale: _Scale
    baseline: str
    height: int = 0

    @property
    def two_columns(self) -> bool:
        """单变体时属性分两栏（§5：1 列「属性可两栏」）。"""
        return self.scale.columns == 1

    def stat_columns(self, variant: _Variant) -> tuple[list[_StatRow], list[_StatRow]]:
        """按两栏切开属性行；单变体才切。"""
        if not self.two_columns:
            return variant.stats, []
        half = (len(variant.stats) + 1) // 2
        return variant.stats[:half], variant.stats[half:]


# ---------------------------------------------------------------- 数值格式


def _format_float(value: float, digits: int = 1) -> str:
    """按固定小数位四舍五入（wiki 区间表是 0.1 精度：``220.5% - 269.5%``）。

    不做「去尾零」处理：``-99.0`` 去掉会变成 ``-99``，和同列的 ``151.9``
    位数不一致，读起来更乱。
    """
    return f"{round(value, digits):.{digits}f}"


def _signed(value: float) -> str:
    """平值词条的带符号文本：``+3.5`` / ``-0.4``（不带 %）。"""
    text = _format_float(abs(value))
    return f"+{text}" if value >= 0 else f"-{text}"


def _format_roll(attr) -> tuple[str, str]:
    """词条的实际数值与理论区间。

    三种单位各按卡面走：

    * 歧视词条 ``x1.06`` → 数值与区间都是倍率（``x1.46 - x1.56``）；
    * 平值词条（穿透 / 攻击范围 / 连击持续时间 / 初始连击 / 格挡角度）→ 数字本身，不带 %；
    * 其余百分比词条 → ``+342.1%`` / ``(293.5% - 358.7%)``。

    区间数据缺失时给「未知」，不要印一个 ``0% - 0%`` 假装算过。
    """
    if attr.discrimination:
        value = f"x{attr.attr:.2f}"
        span = f"(x{1 + attr.low / 100:.2f} - x{1 + attr.high / 100:.2f})"
    elif attr.flat:
        value = _signed(attr.attr)
        span = f"({_format_float(attr.low, 2)} - {_format_float(attr.high, 2)})"
    else:
        value = f"{attr.attr:+.1f}%"
        span = f"({_format_float(attr.low)}% - {_format_float(attr.high)}%)"
    if attr.low == 0 and attr.high == 0:
        span = "(区间未知)"
    return value, span


def _fmt_num(value: float | None, digits: int = 2) -> str:
    """数值去掉无意义的尾零：``140.0`` → ``140``、``5.83`` → ``5.83``。"""
    if value is None:
        return "—"
    text = f"{value:.{digits}f}".rstrip("0").rstrip(".")
    return text or "0"


def _fmt_pct(value: float | None) -> str:
    """0~1 的小数 → ``20.0%``（导出文件里暴击率 / 触发率是小数）。"""
    return "—" if value is None else f"{value * 100:.1f}%"


def _fmt_mult(value: float | None) -> str:
    """倍率 → ``2.0x``。"""
    return "—" if value is None else f"{value:.1f}x"


# ---------------------------------------------------------------- 文案构建


def _split_badge(name: str) -> tuple[str, str]:
    """把变体徽标从武器名里拆出来（``阿利乌双枪 Prime`` → ``阿利乌双枪`` + ``Prime``）。

    徽标单独绘制、永不截断；长名称只截主体。名称里没有徽标时返回原名。
    """
    for badge in _BADGES:
        if badge in name:
            main = name.replace(badge, "").strip(" ·-")
            return (main or name), badge
    return name, ""


def _attr_rows(result: RivenAnalyseResult, palette) -> list[_AttrRow]:
    """共享词条层：把一条结果的词条转成绘制文案。"""
    rows: list[_AttrRow] = []
    for attr in result.attributes or []:
        value, span = _format_roll(attr)
        known = not (attr.low == 0 and attr.high == 0)
        diff = f"| {attr.diff}" if known else ""
        rows.append(
            _AttrRow(
                name=attr.attribute_name,
                value=value,
                span=span,
                diff=diff,
                color=palette.red if diff.startswith("| -") else palette.green,
                known=known,
            )
        )
    return rows


#: 核心属性的固定顺序与取值（§3.1）。返回 ``(标签, 原始值, 展示值)``。
def _raw_stats(profile: WeaponProfile | None) -> list[tuple[str, float | None, str]]:
    if profile is None:
        return []
    return [
        ("基础伤害", profile.total_damage, _fmt_num(profile.total_damage)),
        ("暴击几率", profile.critical_chance, _fmt_pct(profile.critical_chance)),
        ("暴击倍率", profile.critical_multiplier, _fmt_mult(profile.critical_multiplier)),
        ("触发几率", profile.proc_chance, _fmt_pct(profile.proc_chance)),
        ("射速", profile.fire_rate, _fmt_num(profile.fire_rate)),
        ("多重射击", profile.multishot, _fmt_num(profile.multishot)),
    ]


def _stat_matrix(profiles: list[WeaponProfile | None]) -> list[list[_StatRow]]:
    """按 §3.1 生成每个变体的属性行。

    判定依据统一为「值 ≤ 0 或 NULL 视为无此属性」，不做四舍五入
    （``0.004`` 仍算有值，显示为 ``0.0`` 并保留，避免把极小值误删）。
    """
    raw = [_raw_stats(profile) for profile in profiles]
    rows: list[list[_StatRow]] = [[] for _ in profiles]
    if not any(raw):
        return rows

    for index in range(len(raw[0])):
        values = [item[index][1] if index < len(item) else None for item in raw]
        if not any(value is not None and value > 0 for value in values):
            continue  # 全列无值 → 整行不画
        base = values[0] if values[0] and values[0] > 0 else None
        for position, value in enumerate(values):
            missing = value is None or value <= 0
            label, _, text = raw[position][index] if index < len(raw[position]) else ("", None, "")
            if not label:
                continue
            diff = ""
            if not missing and base and position > 0:
                delta = (value - base) / base * 100
                if abs(delta) >= 0.05:
                    diff = f"{delta:+.1f}%"
            rows[position].append(
                _StatRow(label, "—" if missing else text, diff, missing)
            )
    return rows


def _secondary_text(profile: WeaponProfile | None) -> str:
    """次要属性折成一行：``弹匣 12 · 装填 1.4s · 精度 100``（§3.1 第 4 条）。"""
    if profile is None:
        return ""
    parts: list[str] = []
    if profile.magazine_size:
        parts.append(f"弹匣 {profile.magazine_size}")
    if profile.reload_time:
        parts.append(f"装填 {_fmt_num(profile.reload_time)}s")
    if profile.accuracy:
        parts.append(f"精度 {_fmt_num(profile.accuracy)}")
    return " · ".join(parts)


def _blend(first: RGB, second: RGB, ratio: float) -> RGB:
    """两色线性混合（``ratio=0`` 取 first）。"""
    return tuple(  # type: ignore[return-value]
        round(a + (b - a) * ratio) for a, b in zip(first, second, strict=True)
    )


def _tint(palette, index: int, total: int) -> RGB:
    """灰蓝色系取档：自带元素用同色系不同明度区分，不抢紫卡的紫色。

    色带刻意走「蓝 → 青蓝 → 银蓝」，避开紫调——紫色是紫卡新增元素的
    专用语义，自带元素若也偏紫，条上就分不清哪一段是紫卡带来的。
    """
    ramp = [
        palette.blue,
        _blend(palette.blue, palette.icon_credits, 0.6),
        palette.icon_credits,
        palette.icon_platinum,
    ]
    if total <= 1:
        return ramp[0]
    position = index / (total - 1) * (len(ramp) - 1)
    left = min(int(position), len(ramp) - 2)
    return _blend(ramp[left], ramp[left + 1], position - left)


def _segment_colors(shares: list[ElementShare], palette) -> list[RGB]:
    """每段伤害的颜色：自带元素灰蓝，紫卡新增元素紫色。"""
    weapon_total = sum(1 for share in shares if not share.from_riven)
    colors: list[RGB] = []
    weapon_index = 0
    for share in shares:
        if share.from_riven:
            colors.append(palette.rarity_legendary)
        else:
            colors.append(_tint(palette, weapon_index, weapon_total))
            weapon_index += 1
    return colors


def _legend_lines(
    shares: list[ElementShare],
    colors: list[RGB],
    max_width: int,
    text_font,
) -> list[list[tuple[str, RGB]]]:
    """图例按宽度折行（``元素名 数值 (来源)`` 之间用大间距分隔）。

    每项前面带一个色块，宽度按「色块 + 间隙 + 文字」计入。
    """
    lines: list[list[tuple[str, RGB]]] = []
    current: list[tuple[str, RGB]] = []
    cursor = 0
    for share, color in zip(shares, colors, strict=True):
        text = share.label
        item_w = _SWATCH + SPACE["xs"] + C.measure(text, text_font)
        gap = SPACE["lg"] if current else 0
        if current and cursor + gap + item_w > max_width:
            lines.append(current)
            current, cursor, gap = [], 0, 0
        current.append((text, color))
        cursor += gap + item_w
    if current:
        lines.append(current)
    return lines


def _wrap_parts(text: str, max_width: int, text_font, max_lines: int = 2) -> list[str]:
    """按 ``·`` 分段换行。

    通用按空格换行会把 ``精度 100`` 拆成两半，读起来像掉了字；
    这里以分隔符为断点贪心装箱，最多两行。
    """
    parts = [part.strip() for part in text.split("·") if part.strip()]
    lines: list[str] = []
    current = ""
    for part in parts:
        candidate = f"{current} · {part}" if current else part
        if not current or C.measure(candidate, text_font) <= max_width:
            current = candidate
            continue
        lines.append(current)
        current = part
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = C.fit_text(lines[-1] + " · …", max_width, text_font)
    return lines


def _scale_for(columns: int, card_w: int) -> _Scale:
    """按列数取字号规格（§5：3 列时变体名降到 20，估算数字降到 26）。"""
    if columns >= 3:
        return _Scale(columns, card_w, name_size=20, stat_size=16, diff_size=13, estimate_size=26)
    return _Scale(
        columns, card_w, name_size=21, stat_size=_STAT_SIZE, diff_size=14, estimate_size=32
    )


def _columns_for(count: int) -> int:
    """变体数 → 列数（§5：1 / 2 / 3 列，4 个以上走 2 列网格）。"""
    if count <= 1:
        return 1
    if count == 3:
        return 3
    return 2


def _family_name(results: list[RivenAnalyseResult]) -> str:
    """系属：首个变体的主体名（去掉徽标），如 ``阿利乌双枪``。"""
    if not results:
        return ""
    main, _ = _split_badge(results[0].weapon_name)
    return main


def _build_card(group: list[RivenAnalyseResult], total: int, palette) -> _Card:
    """把一个词条分组转成绘制文案。"""
    head = group[0]
    profiles = [result.profile for result in group]
    family = _family_name(group)
    count = len(group)

    if count == 1:
        subtitle = f"{family} · 单变体 · 词条所有变体通用"
    else:
        subtitle = f"{family} 系 · {count} 个变体 · 词条所有变体通用"
    if total > 1:
        subtitle += "（与其它分组词条不同）"

    riven = head.riven_name or "未识别紫卡名"
    info = (
        f"倾向 {head.dot}  {head.omega:.2f}",
        f"段位 {head.profile.mastery_req if head.profile else '—'} · 布局 {head.layout or '—'}",
    )

    same_all = (
        count > 1
        and profiles[0] is not None
        and all(
            profile is not None and profile.same_stats(profiles[0])
            for profile in profiles[1:]
        )
    )
    stats = _stat_matrix(profiles)
    damage_bonus = sum(
        attr.attr for attr in head.attributes or [] if attr.name == DAMAGE_ATTR
    )

    variants: list[_Variant] = []
    for index, result in enumerate(group):
        main, badge = _split_badge(result.weapon_name)
        meta_parts = [result.weapon_type]
        if result.profile is not None and result.profile.mastery_req is not None:
            meta_parts.append(f"段位 {result.profile.mastery_req}")

        shares = (
            build_elements(result.profile, head.attributes, damage_bonus)
            if result.profile is not None and not same_all
            else []
        )
        variants.append(
            _Variant(
                name=main,
                badge=badge,
                meta=" · ".join(part for part in meta_parts if part),
                stats=[] if same_all else stats[index],
                secondary="" if same_all else _secondary_text(result.profile),
                segments=shares,
                hints=element_hints(shares) if shares else [],
                estimate=build_estimate(result.profile, head.attributes)
                if not same_all
                else None,
                same=same_all,
            )
        )

    columns = _columns_for(count)
    return _Card(
        riven=riven,
        subtitle=subtitle,
        info=info,
        attrs=_attr_rows(head, palette),
        variants=variants,
        scale=_scale_for(columns, _COLUMN_WIDTH[columns]),
        baseline=variants[0].name,
    )


# ---------------------------------------------------------------- 测量


def _header_height() -> int:
    """页头高度（标题 30 + 副标题 20 + 分隔线与呼吸）。"""
    return 30 + SPACE["xs"] + FONT["base"] + SPACE["xl"] + 1 + SPACE["xl"]


def _attr_block_height(rows: list[_AttrRow]) -> int:
    """共享词条区高度：小标题 + 每条两行 + 条间距。"""
    if not rows:
        return 0
    return _LABEL_H + SPACE["sm"] + len(rows) * (FONT["base"] + 6 + FONT["sm"] + SPACE["md"])


def _variant_height(card: _Card, variant: _Variant) -> int:
    """单张变体卡的高度（与 :func:`_draw_variant` 的累加顺序一一对应）。"""
    scale = card.scale
    height = _CARD_PAD * 2
    height += scale.name_size + SPACE["xs"]  # 名称 + 徽标
    height += _META_SIZE  # 类型 · 段位
    if variant.same:
        return height + SPACE["lg"] + _HINT_SIZE
    if not variant.stats and not variant.secondary_lines and not variant.segments:
        return height
    height += SPACE["xl"]
    if variant.stats:
        height += _LABEL_H + SPACE["sm"]  # 小标题「属性」
        left, right = card.stat_columns(variant)
        row_h = _ATTR_ROW_H + (_DIFF_LINE_H if variant.stack_diff else 0)
        height += max(len(left), len(right)) * row_h
    if variant.secondary_lines:
        height += SPACE["sm"]
        height += len(variant.secondary_lines) * _SECONDARY_SIZE
        height += (len(variant.secondary_lines) - 1) * SPACE["xs"]
    if variant.segments:
        height += SPACE["xl"]
        height += _composition_height(variant)
    if variant.estimate is not None:
        height += SPACE["xl"]
        height += _estimate_height(variant, card.scale)
    return height


def _estimate_height(variant: _Variant, scale: _Scale) -> int:
    """估算段高度：小标题 + 大字 + 分解行 + DPS 行 + 未计项。"""
    height = _LABEL_H + SPACE["xs"] + 2
    height += scale.estimate_size + SPACE["xs"]
    height += _DECOMP_SIZE
    if variant.estimate is not None and variant.estimate.dps is not None:
        height += _DECOMP_SIZE + 2
    if variant.estimate is not None and variant.estimate.skipped:
        height += SPACE["xs"] + _LABEL_SIZE + 2
    # 末行字形会比标称行高多下探几像素，补一点避免贴边
    return height + SPACE["xs"]


def _composition_height(variant: _Variant) -> int:
    """伤害构成段高度：小标题 + 条 + 图例 + 组合提示（不含段前间距）。"""
    height = _LABEL_H + SPACE["sm"] + _BAR_H + SPACE["sm"]
    height += len(variant.legend_lines) * (_LEGEND_SIZE + SPACE["xs"])
    if variant.hints:
        height += SPACE["xs"] + len(variant.hints) * (_HINT_SIZE + 2)
    return height


def _section_header_height() -> int:
    """区头「武器变体 / 差异基准」高度。"""
    return SPACE["lg"] + 1 + SPACE["md"] + _LABEL_H + SPACE["lg"]


def _footnote_height() -> int:
    return SPACE["xl"] + _FOOTNOTE_SIZE


# ---------------------------------------------------------------- 绘制


def _draw_tracked(cb, text: str, x: int, y: int, text_font, tracking: float) -> int:
    """逐字绘制并加字距（PIL 没有 letter-spacing，只能自己排）。

    Returns:
        文本实际占用的宽度。
    """
    cursor = x
    for char in text:
        cb.add_text(char, int(cursor), y)
        cursor += C.measure(char, text_font) + tracking
    return int(cursor - x - tracking) if text else 0


def _draw_section_label(page, text: str, x: int, y: int) -> None:
    """区块小标题：13px + 0.12em 字距 + 弱化色。"""
    page.cb.set_color(page.palette.text_dim).set_font(font_px(_LABEL_SIZE, bold=True))
    _draw_tracked(page.cb, text, x, y, font_px(_LABEL_SIZE, bold=True), _LABEL_TRACKING)


def _draw_header(page, card: _Card) -> int:
    """A 区：紫卡名 + 系属 + 右侧倾向信息。"""
    palette = page.palette
    cb = page.cb
    x = page.content_x
    right = x + page.content_w
    y = page.content_y

    info_font = font_px(16)
    info_w = max(C.measure(line, info_font) for line in card.info)
    title_font = font_px(30, bold=True)
    title = C.fit_text(card.riven, page.content_w - info_w - SPACE["xl"], title_font)

    cb.set_color(palette.rarity_legendary).set_font(title_font)
    cb.add_text(title, x, y)

    for index, line in enumerate(card.info):
        cb.set_color(palette.text_muted).set_font(info_font)
        cb.add_text(line, right - C.measure(line, info_font), y + index * 20)

    y += 30 + SPACE["xs"]
    sub_font = font("base")
    cb.set_color(palette.text_muted).set_font(sub_font)
    cb.add_text(C.fit_text(card.subtitle, page.content_w, sub_font), x, y)

    y += FONT["base"] + SPACE["xl"]
    C.draw_divider(page, y)
    return y + 1 + SPACE["xl"]


def _draw_attributes(page, rows: list[_AttrRow], y: int) -> int:
    """B 区：共享词条，每条两行。"""
    palette = page.palette
    cb = page.cb
    x = page.content_x
    right = x + page.content_w

    _draw_section_label(page, "词条 · 所有变体通用", x, y)
    y += _LABEL_H + SPACE["sm"]

    name_font = font("base")
    value_font = font("md", bold=True)
    span_font = font("sm")
    diff_font = font_px(18, bold=True)

    for row in rows:
        value_w = C.measure(row.value, value_font)
        cb.set_color(palette.text).set_font(name_font)
        cb.add_text(
            C.fit_text(row.name, page.content_w - value_w - SPACE["lg"], name_font),
            x,
            y,
        )
        cb.set_color(palette.text).set_font(value_font)
        cb.add_text(row.value, right - value_w, y - 2)

        line2 = y + FONT["base"] + 6
        cb.set_color(palette.text_muted).set_font(span_font)
        cb.add_text(row.span, x, line2)
        if row.diff:
            cb.set_color(row.color).set_font(diff_font)
            cb.add_text(row.diff, right - C.measure(row.diff, diff_font), line2 - 2)

        y += FONT["base"] + 6 + FONT["sm"] + SPACE["md"]
    return y


def _draw_variant_head(page, variant: _Variant, scale: _Scale, x: int, y: int, width: int) -> int:
    """变体身份：名称（徽标不截断）+ 类型 · 段位。"""
    palette = page.palette
    cb = page.cb
    name_font = font_px(scale.name_size, bold=True)
    badge_font = font_px(max(12, scale.name_size - 6), bold=True)

    badge_w = C.measure(variant.badge, badge_font) + SPACE["sm"] if variant.badge else 0
    cb.set_color(palette.gold).set_font(name_font)
    cb.add_text(C.fit_text(variant.name, width - badge_w, name_font), x, y)
    if variant.badge:
        cb.set_color(palette.rarity_legendary).set_font(badge_font)
        cb.add_text(
            variant.badge,
            x + width - badge_w + SPACE["sm"],
            y + max(0, scale.name_size - getattr(badge_font, "size", scale.name_size)),
        )

    y += scale.name_size + SPACE["xs"]
    meta_font = font_px(_META_SIZE)
    cb.set_color(palette.text_muted).set_font(meta_font)
    cb.add_text(C.fit_text(variant.meta, width, meta_font), x, y)
    return y + _META_SIZE


def _draw_stat_rows(
    page,
    rows: list[_StatRow],
    x: int,
    y: int,
    width: int,
    scale: _Scale,
    show_diff: bool,
    stacked: bool = False,
) -> int:
    """一栏属性行：标签左、数值右、差异贴右（金色）。

    Args:
        stacked: 差异另起一行（3 列窄卡放不下三段并排时用），返回累加后的 y。
        show_diff: 是否画差异。

    Returns:
        累加后的 y。
    """
    palette = page.palette
    cb = page.cb
    right = x + width
    label_font = font_px(scale.stat_size)
    value_font = font_px(scale.stat_size, bold=True)
    diff_font = font_px(scale.diff_size)
    row_h = _ATTR_ROW_H + _DIFF_LINE_H if stacked else _ATTR_ROW_H

    for row in rows:
        diff = row.diff if show_diff else ""
        diff_w = 0 if stacked else (C.measure(diff, diff_font) + SPACE["sm"] if diff else 0)
        value_w = C.measure(row.value, value_font)
        text_y = y + (_ATTR_ROW_H - scale.stat_size) // 2

        cb.set_color(palette.text_muted).set_font(label_font)
        cb.add_text(
            C.fit_text(row.label, width - value_w - diff_w - SPACE["sm"], label_font),
            x,
            text_y,
        )
        cb.set_color(palette.text_dim if row.missing else palette.text).set_font(value_font)
        cb.add_text(row.value, right - diff_w - value_w, text_y)
        if diff:
            cb.set_color(palette.gold).set_font(diff_font)
            cb.add_text(
                diff,
                right - C.measure(diff, diff_font),
                y + _ATTR_ROW_H - 4 if stacked else text_y + 3,
            )
        y += row_h
    return y


def _draw_composition(page, variant: _Variant, x: int, y: int, width: int) -> int:
    """伤害构成：横向堆叠条 + 图例 + 复合元素提示（§3.2）。"""
    palette = page.palette
    cb = page.cb

    _draw_section_label(page, "伤害构成", x, y)
    y += _LABEL_H + SPACE["sm"]

    total = sum(share.value for share in variant.segments) or 1.0
    colors = _segment_colors(variant.segments, palette)
    cursor = x
    for index, (share, color) in enumerate(zip(variant.segments, colors, strict=True)):
        last = index == len(variant.segments) - 1
        segment_w = (
            width - (cursor - x)
            if last
            else max(2, round(width * share.value / total))
        )
        cb.set_color(color)
        cb.fill_rect(cursor, y, max(0, segment_w), _BAR_H)
        # 段间留 1px 缝：同一色系的相邻段在 10px 高时几乎分不开
        if not last:
            cb.set_color(palette.surface_alt)
            cb.fill_rect(cursor + segment_w - 1, y, 1, _BAR_H)
        cursor += segment_w
    y += _BAR_H + SPACE["sm"]

    legend_font = font_px(_LEGEND_SIZE)
    for line in variant.legend_lines:
        cursor = x
        for text, color in line:
            cb.set_color(color)
            cb.fill_rect(cursor, y + (_LEGEND_SIZE - _SWATCH) // 2, _SWATCH, _SWATCH)
            cursor += _SWATCH + SPACE["xs"]
            cb.set_color(palette.text_muted).set_font(legend_font)
            cb.add_text(text, cursor, y)
            cursor += C.measure(text, legend_font) + SPACE["lg"]
        y += _LEGEND_SIZE + SPACE["xs"]

    if variant.hints:
        y += SPACE["xs"]
        hint_font = font_px(_HINT_SIZE)
        for hint in variant.hints:
            cb.set_color(palette.text_dim).set_font(hint_font)
            cb.add_text(C.fit_text(hint, width, hint_font), x, y)
            y += _HINT_SIZE + 2
    return y


def _estimate_lines(
    estimate: RivenEstimate, width: int
) -> tuple[str, str | None, str | None]:
    """估算段的文案：乘数分解优先给全，放不下就逐级简化。

    Returns:
        ``(分解行, DPS 副行, 未计项行)``，后两项可能为 ``None``。
    """
    full = (
        f"{estimate.base_damage:,.0f} 基础"
        f" ×{estimate.element_factor:.2f} 元素"
        f" ×{estimate.crit_factor:.2f} 暴击"
    )
    short = f"×{estimate.element_factor:.2f} 元素 ×{estimate.crit_factor:.2f} 暴击"
    decomp_font = font_px(_DECOMP_SIZE)
    decomp = full if C.measure(full, decomp_font) <= width else short
    if C.measure(decomp, decomp_font) > width:
        decomp = C.fit_text(decomp, width, decomp_font)

    dps_line: str | None = None
    if estimate.dps is not None:
        gain = estimate.dps_gain
        suffix = f"  {gain:+.1f}%" if gain is not None else ""
        dps_line = f"DPS {estimate.dps:,.0f}{suffix}"
    skipped = "未计：" + "、".join(estimate.skipped) if estimate.skipped else None
    return decomp, dps_line, skipped


def _draw_estimate(page, variant: _Variant, scale: _Scale, x: int, y: int, width: int) -> int:
    """紫卡加成后估算：单发期望大字 + 乘数分解 + DPS 副行 + 未计项（§4.2）。"""
    estimate = variant.estimate
    if estimate is None:
        return y

    palette = page.palette
    cb = page.cb

    _draw_section_label(page, "紫卡加成后 · 单发期望", x, y)
    y += _LABEL_H + SPACE["xs"] + 2

    big_font = font_px(scale.estimate_size, bold=True)
    gain_font = font_px(16, bold=True)
    number = f"{estimate.per_shot:,.0f}"
    gain = f"{estimate.per_shot_gain:+.1f}%"
    cb.set_color(palette.text).set_font(big_font)
    cb.add_text(number, x, y)
    cb.set_color(palette.gold).set_font(gain_font)
    cb.add_text(
        gain,
        x + width - C.measure(gain, gain_font),
        y + max(0, scale.estimate_size - 16 - 2),
    )
    y += scale.estimate_size + SPACE["xs"]

    decomp, dps_line, skipped = _estimate_lines(estimate, width)
    decomp_font = font_px(_DECOMP_SIZE)
    cb.set_color(palette.text_dim).set_font(decomp_font)
    cb.add_text(decomp, x, y)
    y += _DECOMP_SIZE

    if dps_line:
        y += 2
        cb.set_color(palette.text_muted).set_font(decomp_font)
        cb.add_text(C.fit_text(dps_line, width, decomp_font), x, y)
        y += _DECOMP_SIZE

    if skipped:
        y += SPACE["xs"]
        skip_font = font_px(_LABEL_SIZE)
        cb.set_color(palette.text_dim).set_font(skip_font)
        cb.add_text(C.fit_text(skipped, width, skip_font), x, y)
        y += _LABEL_SIZE + 2
    return y


def _draw_variant(page, card: _Card, variant: _Variant, x: int, y: int, width: int) -> None:
    """D 区：一张变体卡。"""
    palette = page.palette
    cb = page.cb
    scale = card.scale
    height = _variant_height(card, variant)

    cb.draw_rounded_rect(
        x, y, width, height,
        radius=RADIUS["md"],
        fill=palette.surface_alt,
        outline=palette.border,
        stroke_width=1,
    )

    inner_x = x + _CARD_PAD
    inner_w = width - _CARD_PAD * 2
    cursor = _draw_variant_head(page, variant, scale, inner_x, y + _CARD_PAD, inner_w)

    if variant.same:
        hint_font = font_px(_HINT_SIZE)
        cb.set_color(palette.text_dim).set_font(hint_font)
        cb.add_text(
            C.fit_text("属性一致，仅名称不同", inner_w, hint_font),
            inner_x,
            cursor + SPACE["lg"],
        )
        return

    cursor += SPACE["xl"]
    left, right = card.stat_columns(variant)
    if left or right:
        _draw_section_label(page, "属性", inner_x, cursor)
        cursor += _LABEL_H + SPACE["sm"]

        row_h = _ATTR_ROW_H + (_DIFF_LINE_H if variant.stack_diff else 0)
        start_y = cursor
        if right:
            column_w = (inner_w - SPACE["3xl"]) // 2
            _draw_stat_rows(
                page, left, inner_x, start_y, column_w, scale, variant.show_diff, variant.stack_diff
            )
            _draw_stat_rows(
                page,
                right,
                inner_x + column_w + SPACE["3xl"],
                start_y,
                column_w,
                scale,
                variant.show_diff,
                variant.stack_diff,
            )
        else:
            _draw_stat_rows(
                page, left, inner_x, start_y, inner_w, scale, variant.show_diff, variant.stack_diff
            )
        cursor = start_y + max(len(left), len(right)) * row_h

    if variant.secondary_lines:
        cursor += SPACE["sm"]
        sec_font = font_px(_SECONDARY_SIZE)
        cb.set_color(palette.text_muted).set_font(sec_font)
        for line in variant.secondary_lines:
            cb.add_text(line, inner_x, cursor)
            cursor += _SECONDARY_SIZE + SPACE["xs"]

    if variant.segments:
        cursor += SPACE["xl"]
        cursor = _draw_composition(page, variant, inner_x, cursor, inner_w)

    if variant.estimate is not None:
        cursor += SPACE["xl"]
        cursor = _draw_estimate(page, variant, scale, inner_x, cursor, inner_w)


def _draw_variant_header(page, card: _Card, y: int) -> int:
    """C 区：左「武器变体」，右「差异以 X 为基准」。"""
    palette = page.palette
    x = page.content_x
    right = x + page.content_w

    y += SPACE["lg"]
    C.draw_divider(page, y)
    y += 1 + SPACE["md"]

    _draw_section_label(page, "武器变体", x, y)
    note_font = font_px(_FOOTNOTE_SIZE)
    note = C.fit_text(
        f"差异以「{card.baseline}」为基准", page.content_w // 2, note_font
    )
    page.cb.set_color(palette.text_dim).set_font(note_font)
    page.cb.add_text(note, right - C.measure(note, note_font), y)
    return y + _LABEL_H + SPACE["lg"]


def _draw_footnote(page, y: int) -> int:
    """E 区：口径声明（必须出现，估算值不是游戏内实际伤害）。"""
    page.cb.set_color(page.palette.text_dim).set_font(font_px(_FOOTNOTE_SIZE))
    page.cb.add_text(
        C.fit_text(_DISCLAIMER, page.content_w, font_px(_FOOTNOTE_SIZE)),
        page.content_x,
        y + SPACE["xl"],
    )
    return y + _footnote_height()


# ---------------------------------------------------------------- 入口


def _group_results(
    results: list[RivenAnalyseResult],
) -> list[list[RivenAnalyseResult]]:
    """按词条指纹分组。

    跨武器类型（极少数）时同一条词条的区间会不同，共享层只能画一份，
    于是按指纹拆成多张卡，各自带自己的词条层。
    """
    groups: list[list[RivenAnalyseResult]] = []
    signatures: list[tuple] = []
    for result in results:
        signature = result.attribute_signature()
        if signature in signatures:
            groups[signatures.index(signature)].append(result)
        else:
            signatures.append(signature)
            groups.append([result])
    return groups


def _diff_fits(card: _Card, variant: _Variant, inner_w: int) -> bool:
    """本卡的差异值放得下吗。

    3 列时列宽只有 216，``暴击几率 32.0% +45.5%`` 三段挤在一行会把属性名
    截成「暴…」。宁可整卡不画差异，也不能把属性名截掉——属性名是识别
    这一行是什么的唯一线索。
    """
    label_font = font_px(card.scale.stat_size)
    value_font = font_px(card.scale.stat_size, bold=True)
    diff_font = font_px(card.scale.diff_size)
    width = (inner_w - SPACE["3xl"]) // 2 if card.two_columns else inner_w
    for row in variant.stats:
        if not row.diff:
            continue
        need = (
            C.measure(row.label, label_font)
            + C.measure(row.value, value_font)
            + C.measure(row.diff, diff_font)
            + SPACE["sm"] * 2
        )
        if need > width:
            return False
    return True


def _finalize_card(card: _Card, content_w: int, palette) -> None:
    """定稿：按最终列宽切次要属性串、决定是否画差异、算出卡高。"""
    columns = card.scale.columns
    available = (content_w - (columns - 1) * _GAP) // columns
    card.scale = _Scale(
        columns,
        min(_COLUMN_WIDTH[columns], available),
        card.scale.name_size,
        card.scale.stat_size,
        card.scale.diff_size,
        card.scale.estimate_size,
    )

    inner_w = card.scale.card_w - _CARD_PAD * 2
    sec_font = font_px(_SECONDARY_SIZE)
    legend_font = font_px(_LEGEND_SIZE)
    # 是否折行按整卡决定：只要有一张卡的差异放不下，全部卡都折行，
    # 否则同一行里各卡行高不同，跨列纵向对齐立刻崩掉。
    stack = any(not _diff_fits(card, variant, inner_w) for variant in card.variants)
    for variant in card.variants:
        variant.secondary_lines = (
            _wrap_parts(variant.secondary, inner_w, sec_font) if variant.secondary else []
        )
        variant.legend_lines = (
            _legend_lines(
                variant.segments,
                _segment_colors(variant.segments, palette),
                inner_w,
                legend_font,
            )
            if variant.segments
            else []
        )
        variant.stack_diff = stack

    rows = [
        card.variants[start : start + columns]
        for start in range(0, len(card.variants), columns)
    ]
    grid_h = sum(
        max(_variant_height(card, variant) for variant in row) for row in rows
    ) + max(0, len(rows) - 1) * _GAP
    card.height = (
        _header_height()
        + _attr_block_height(card.attrs)
        + _section_header_height()
        + grid_h
        + _footnote_height()
    )


def render_riven_analyse_card(
    renderer: CardRenderer,
    results: list[RivenAnalyseResult],
) -> Image.Image:
    """绘制紫卡分析卡片。

    Args:
        renderer: CardRenderer 实例（空数据时用它出提示图）。
        results: 紫卡分析结果列表（每个元素是一把候选变体）。

    Returns:
        PIL Image 对象。
    """
    if not results:
        return renderer.create_text_image("未识别到紫卡信息", 1040, 156)

    theme = current_theme()
    palette = theme.palette
    groups = _group_results(results)
    cards = [_build_card(group, len(groups), palette) for group in groups]

    # ---- 画布宽：取最宽一张卡的网格需求，夹到 [MIN_WIDTH, MAX_WIDTH] ----
    def grid_width(card: _Card) -> int:
        columns = card.scale.columns
        return columns * _COLUMN_WIDTH[columns] + (columns - 1) * _GAP

    canvas_w = min(MAX_WIDTH, max(MIN_WIDTH, max(grid_width(card) for card in cards) + PAD * 2))
    content_w = canvas_w - PAD * 2

    for card in cards:
        _finalize_card(card, content_w, palette)

    total_h = sum(card.height for card in cards) + max(0, len(cards) - 1) * SPACE["xl"]
    size = measure_card_size(
        CardSpec(
            blocks=[CustomBlock(width=content_w, height=total_h)],
            standing="md",
        )
    )

    page = C.new_page(theme, size.width, size.height)
    y = page.content_y

    for card_index, card in enumerate(cards):
        if card_index:
            y += SPACE["xl"]
        y = _draw_header(page, card)
        y = _draw_attributes(page, card.attrs, y)
        y = _draw_variant_header(page, card, y)

        columns = card.scale.columns
        grid_w = columns * card.scale.card_w + (columns - 1) * _GAP
        grid_x = page.content_x + max(0, (page.content_w - grid_w) // 2)
        offset = 0
        for start in range(0, len(card.variants), columns):
            row = card.variants[start : start + columns]
            row_h = max(_variant_height(card, variant) for variant in row)
            for index, variant in enumerate(row):
                _draw_variant(
                    page,
                    card,
                    variant,
                    grid_x + index * (card.scale.card_w + _GAP),
                    y + offset,
                    card.scale.card_w,
                )
            offset += row_h + _GAP
        if card.variants:
            y += offset - _GAP
        y = _draw_footnote(page, y)

    frame.draw_standing_block(page, y, "md")
    frame.draw_footer_block(page)
    return page.cb.to_image()
