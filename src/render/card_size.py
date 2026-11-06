"""Card sizing / 数据驱动的卡片尺寸

**唯一职责**：根据「卡片要展示什么」算出画布该多大。绘图模块不再自己算宽高，
一律先调 :func:`measure_card_size`，再按返回的 ``width`` / ``height`` 建页。

尺寸来源（全部由数据字段推导，不含固定画布值）
------------------------------------------------

宽度（取各块所需宽度的最大值，再夹到 ``limits``）::

    header_w = measure(title, 2xl, bold) + (subtitle ? SPACE["3xl"] + measure(subtitle, base) : 0)
    chips_w  = Σ measure(label, sm) + SPACE["sm"] + measure(value, md) + SPACE["3xl"] * (n-1)
    kv_w     = max(measure(label, sm)) + SPACE["xl"] + max(measure(value, md))
    table_w  = Σ 每列自然宽（表头 / 最宽单元格 / min_width 取大 + SPACE["md"]*2）
    grid_w   = columns * card_min_width + (columns - 1) * gap
    text_w   = max(measure(line, size))
    custom_w = 调用方声明的固有宽度
    content_w = max(以上各项, MIN_CONTENT_W)          # 避免内容太少时过窄
    width     = clamp(content_w + PAD * 2, min_width, max_width)

高度（自上而下累加）::

    header_h  = title ? FONT["2xl"] + SPACE["xl"] * 2 : 0
    chips_h   = FONT["md"] + SPACE["md"]
    kv_h      = rows * (FONT["md"] + SPACE["md"])
    table_h   = 表头(FONT["base"] + SPACE["xl"]) + SPACE["xs"] + rows * 行高
    text_h    = lines * (字号 + SPACE["xs"])
    grid_h    = rows * card_height + (rows - 1) * gap
    custom_h  = 调用方声明的固有高度
    standing_h= 立绘高（按档位等比缩放）+ SPACE["xl"]；关闭时为 0
    height    = clamp(content_top + header_h + header_gap
                      + Σ (block_h + block.gap)
                      + standing_h + footer_space, min_h, max_h)

``block.gap`` 是**该块之后**的间距（默认 0，需要时显式给），
因此最后一个块留 0 即可，不会和看板娘的呼吸间距叠加。

宽高比协调（不拉伸、只补留白）
------------------------------

::

    aspect = height / width
    aspect > max_aspect（太瘦）→ width = min(ceil(height / max_aspect), max_width)
    aspect < min_aspect（太扁）→ height = min(ceil(width * min_aspect), max_height)

补的是空白，不是缩放：所有绘制仍按 1:1 像素坐标，字体与间距不变，
因此不会有拉伸失真；内容偏上、页脚贴底，中间自然留白。

边界处理
--------

=============== =====================================================
情况            策略
=============== =====================================================
无任何块        返回 ``min_width × min_height``，仍可画页脚/看板娘
``None`` / NaN  字段按「无内容」处理，宽度贡献 0，不参与 max
负数 / 异常尺寸 块尺寸走 ``max(0, ...)``，不会把画布算小
超长文本        宽度先被 ``max_width`` 夹住；绘制侧 ``fit_text`` 截断
极端宽高比      见上，补留白到 ``[min_aspect, max_aspect]``
高度超限        夹到 ``max_height``；内容由调用方分页/截断
看板娘关闭      不占高度，卡片自动变矮
=============== =====================================================

调用示例
--------

.. code-block:: python

    from .card_size import CardSpec, TableBlock, measure_card_size

    size = measure_card_size(
        CardSpec(
            title="突击任务",
            subtitle=f"Boss: {boss_name}",
            blocks=[TableBlock(columns=columns, rows=rows)],
            standing="md",
        )
    )
    page = C.new_page(theme, size.width, size.height)

返回值 :class:`CardSize` 带诊断字段（``intrinsic_*`` / ``padded``），
便于测试和日志定位「为什么这张卡这么高」。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

from . import card_frame as frame
from . import components as C
from .design import FONT, MAX_WIDTH, MIN_WIDTH, PAD, SPACE, font

#: 内容区最小宽度（画布再窄，内容也不至于挤成一列）。
MIN_CONTENT_W = 560

#: 默认尺寸上下限。
DEFAULT_MIN_WIDTH = MIN_WIDTH
DEFAULT_MAX_WIDTH = MAX_WIDTH
DEFAULT_MIN_HEIGHT = 240
DEFAULT_MAX_HEIGHT = 4000

#: 默认宽高比区间（height / width）。
DEFAULT_MIN_ASPECT = 0.35   # 太扁：height 至少为 width 的 35%
DEFAULT_MAX_ASPECT = 3.6    # 太瘦：width 至少为 height 的 1/3.6


@dataclass(frozen=True)
class SizeLimits:
    """画布约束（全部有默认值，调用方只覆盖需要的）。"""

    min_width: int = DEFAULT_MIN_WIDTH
    max_width: int = DEFAULT_MAX_WIDTH
    min_height: int = DEFAULT_MIN_HEIGHT
    max_height: int = DEFAULT_MAX_HEIGHT
    min_aspect: float = DEFAULT_MIN_ASPECT
    max_aspect: float = DEFAULT_MAX_ASPECT


DEFAULT_LIMITS = SizeLimits()


# ------------------------------------------------------------------ 块描述


@dataclass(frozen=True)
class ChipsBlock:
    """一行「标签 + 值」。"""

    chips: Sequence[tuple[str, str]]
    gap: int = SPACE["md"]


@dataclass(frozen=True)
class KvBlock:
    """竖排键值块。"""

    rows: Sequence[tuple]
    label_width: int = 0
    gap: int = SPACE["md"]


@dataclass(frozen=True)
class TableBlock:
    """表格（表头 + 数据行）。"""

    columns: Sequence[C.Column]
    rows: Sequence[Sequence[tuple]]
    gap: int = 0


@dataclass(frozen=True)
class TextBlock:
    """纯文本行（自定义块的最小替代）。"""

    lines: Sequence[str]
    size: str = "md"
    gap: int = 0


@dataclass(frozen=True)
class GridBlock:
    """网格（卡片宽高由调用方按数据算好）。"""

    columns: int
    card_min_width: int
    card_height: int
    rows: int = 1
    gap: int = SPACE["lg"]


@dataclass(frozen=True)
class CustomBlock:
    """自定义绘制块：由调用方声明固有宽高。"""

    width: int
    height: int
    gap: int = 0


@dataclass(frozen=True)
class CardSpec:
    """一张卡要展示的内容描述。"""

    title: str = ""
    subtitle: str = ""
    blocks: Sequence[object] = field(default_factory=tuple)
    #: 页头与第一个块之间的间距（默认 0，需要呼吸的卡显式给）。
    header_gap: int = 0
    #: 看板娘档位；``None`` 表示不占高度（卡片自己画在网格空位里）。
    standing: str | None = "md"
    #: 数据里的季节（如 1999 日历）；给了就按它换装。
    standing_season: str | None = None
    #: 页脚；空串 = 用品牌设置的全局署名，``None`` = 不画。
    footer: str | None = ""
    limits: SizeLimits = DEFAULT_LIMITS
    #: 额外宽度需求（并排双表、侧栏等无法用块表达的排版）。
    extra_width: int = 0


@dataclass(frozen=True)
class CardSize:
    """尺寸计算结果。"""

    width: int
    height: int
    content_width: int
    content_height: int
    intrinsic_width: int
    intrinsic_height: int
    aspect: float
    #: 是否因宽高比约束补了留白
    padded: bool


# ------------------------------------------------------------------ 工具


def _safe(value: object) -> int:
    """把任意数值收敛成非负整数；``None`` / NaN / inf / 负数 → 0。"""
    if value is None:
        return 0
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0
    if not math.isfinite(number) or number <= 0:
        return 0
    return int(number)


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _block_width(block: object) -> int:
    if isinstance(block, ChipsBlock):
        return C.measure_chips([tuple(chip) for chip in block.chips])
    if isinstance(block, KvBlock):
        return C.measure_kv(list(block.rows), block.label_width)
    if isinstance(block, TableBlock):
        return C.measure_table(list(block.columns), list(block.rows))
    if isinstance(block, TextBlock):
        text_font = font(block.size)
        return max((C.measure(line, text_font) for line in block.lines), default=0)
    if isinstance(block, GridBlock):
        columns = max(1, _safe(block.columns))
        return columns * _safe(block.card_min_width) + (columns - 1) * _safe(block.gap)
    if isinstance(block, CustomBlock):
        return _safe(block.width)
    return 0


def _block_height(block: object) -> int:
    if isinstance(block, ChipsBlock):
        return FONT["md"] + SPACE["md"]
    if isinstance(block, KvBlock):
        return len(block.rows) * (FONT["md"] + SPACE["md"])
    if isinstance(block, TableBlock):
        return C.table_height(len(block.rows))
    if isinstance(block, TextBlock):
        size = FONT.get(block.size, FONT["md"])
        return len(block.lines) * (size + SPACE["xs"])
    if isinstance(block, GridBlock):
        rows = max(0, _safe(block.rows))
        gap = _safe(block.gap)
        return rows * _safe(block.card_height) + max(0, rows - 1) * gap
    if isinstance(block, CustomBlock):
        return _safe(block.height)
    return 0


def measure_card_size(spec: CardSpec) -> CardSize:
    """按内容描述算出画布尺寸。

    Args:
        spec: 卡片内容描述（标题、块列表、看板娘档位、页脚、约束）。

    Returns:
        :class:`CardSize`：``width`` / ``height`` 直接用于 ``new_page``；
        ``content_height`` 是内容实际占用的高度（不含宽高比补白）。
    """
    limits = spec.limits

    # ---- 宽度：各块所需宽度的最大值 ----
    intrinsic_w = _safe(spec.extra_width)
    for block in spec.blocks:
        intrinsic_w = max(intrinsic_w, _block_width(block))
    intrinsic_w = max(
        intrinsic_w,
        C.measure_header(spec.title, spec.subtitle) if spec.title else 0,
        MIN_CONTENT_W,
    )
    width = _clamp(intrinsic_w + PAD * 2, limits.min_width, limits.max_width)

    # ---- 高度：页头 + 各块（含块后间距）+ 看板娘 + 页脚 ----
    content_h = 0
    if spec.title:
        content_h += FONT["2xl"] + SPACE["xl"] * 2 + _safe(spec.header_gap)
    last = len(spec.blocks) - 1
    for index, block in enumerate(spec.blocks):
        content_h += _block_height(block)
        # 最后一个块的“块后间距”没有下一块可隔，不计入（否则会和看板娘的呼吸叠加）
        if index != last:
            content_h += _safe(getattr(block, "gap", 0))

    content_w = width - PAD * 2
    standing_h = (
        frame.standing_block_height(spec.standing, content_w, spec.standing_season)
        if spec.standing
        else 0
    )

    content_h = C.content_top() + content_h + standing_h
    footer_h = 0 if spec.footer is None else C.footer_space()
    height = _clamp(content_h + footer_h, limits.min_height, limits.max_height)

    # ---- 宽高比：只补留白，不缩放内容 ----
    padded = False
    aspect = height / width if width else 0.0
    if aspect > limits.max_aspect:
        target_w = math.ceil(height / limits.max_aspect)
        if target_w > width:
            width = _clamp(target_w, limits.min_width, limits.max_width)
            padded = True
    elif aspect < limits.min_aspect:
        target_h = math.ceil(width * limits.min_aspect)
        if target_h > height:
            height = _clamp(target_h, limits.min_height, limits.max_height)
            padded = True

    return CardSize(
        width=width,
        height=height,
        content_width=width - PAD * 2,
        content_height=min(content_h, height),
        intrinsic_width=intrinsic_w,
        intrinsic_height=content_h,
        aspect=round(height / width, 3) if width else 0.0,
        padded=padded,
    )


def describe(spec: CardSpec) -> dict[str, int | float | bool]:
    """把尺寸结果转成可日志/可断言的字典（排障用）。"""
    size = measure_card_size(spec)
    return {
        "width": size.width,
        "height": size.height,
        "content_width": size.content_width,
        "content_height": size.content_height,
        "intrinsic_width": size.intrinsic_width,
        "intrinsic_height": size.intrinsic_height,
        "aspect": size.aspect,
        "padded": size.padded,
    }
