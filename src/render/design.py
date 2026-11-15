"""Design tokens / 设计令牌

卡片渲染的统一规格：画布、间距、字阶、圆角、两套主题色板。

规则（改卡时遵守）：

- **画布宽由内容决定**：卡片先量出「内容需要多宽」，再交给 ``resolve_width()``
  夹到 ``[MIN_WIDTH, MAX_WIDTH]``；不要写死宽度。
- **字号只能取 ``FONT`` 里的 7 档**，不要写 21、26 这种中间值；
- **间距只能取 ``SPACE`` 的 7 档**；
- **颜色只能取 ``Theme.palette``**，卡片里禁止裸 RGB；
- 圆角只有 3 档。

设计稿见 ``plans/card_redesign_2026-11-04.md``。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from PIL import ImageFont

RGB = tuple[int, int, int]

# ---------------------------------------------------------------- 画布
MIN_WIDTH = 720
"""最窄画布宽（像素）。内容再少也不低于这个值，否则看板娘会把正文挤没。"""

MAX_WIDTH = 1600
"""最宽画布宽（像素）。内容再多也不超过这个值，超出部分由 ``fit_text`` 截断。"""

PAD = 40
"""画布外边距。"""

INNER_PAD = 32
"""卡面内边距。"""


def resolve_width(content_intrinsic: int) -> int:
    """把「内容需要多宽」换算成画布宽。

    Args:
        content_intrinsic: 内容区所需的像素宽（由 ``components.measure_*`` 量出）。

    Returns:
        画布宽度，夹在 ``[MIN_WIDTH, MAX_WIDTH]`` 之间。
    """
    return max(MIN_WIDTH, min(MAX_WIDTH, content_intrinsic + PAD * 2))

# ---------------------------------------------------------------- 字阶（7 档）
FONT = {
    "xs": 14,   # 角标、序号
    "sm": 16,   # 页脚、备注
    "base": 20,  # 表头、提示、奖励名
    "md": 24,   # 正文、表格行
    "lg": 30,   # 区块标题、价格
    "xl": 36,   # 页面副标题
    "2xl": 48,  # 页面标题
}

# ---------------------------------------------------------------- 间距（7 档）
SPACE = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24, "2xl": 32, "3xl": 48}

# ---------------------------------------------------------------- 圆角（3 档）
RADIUS = {"sm": 8, "md": 14, "lg": 20}


@dataclass(frozen=True)
class Palette:
    """一套配色。字段是语义，不是颜色名。"""

    canvas: RGB      # 画布底色（卡片圆角外的部分）
    surface: RGB     # 卡面
    surface_alt: RGB  # 斑马纹 / 次级容器
    border: RGB      # 边框、分割线
    text: RGB        # 主文本
    text_muted: RGB  # 次要文本
    text_dim: RGB    # 弱化文本（页脚、提示）
    gold: RGB        # 强调金：价格、序号、标题点缀
    blue: RGB        # 强调蓝：标题、链接
    green: RGB       # 成功 / 在线
    amber: RGB       # 警告
    red: RGB         # 危险 / 离线
    rarity_common: RGB     # 遗物奖励：常见（铜）
    rarity_uncommon: RGB   # 遗物奖励：罕见（银）
    rarity_rare: RGB       # 遗物奖励：稀有（金）
    rarity_legendary: RGB  # 遗物奖励：传说（紫）
    # Warframe 图标字体里三种货币的固定配色，明暗主题各一版（色相不变，只调明度）
    icon_credits: RGB      # 信用点（青）
    icon_ducats: RGB       # 杜卡德（金）
    icon_platinum: RGB     # 白金（银蓝）


DARK = Palette(
    canvas=(10, 13, 22),
    surface=(20, 25, 38),
    surface_alt=(27, 34, 51),
    border=(41, 50, 74),
    text=(241, 244, 250),
    text_muted=(152, 162, 184),
    text_dim=(107, 117, 144),
    gold=(230, 180, 80),
    blue=(91, 141, 239),
    green=(67, 208, 138),
    amber=(242, 184, 75),
    red=(239, 91, 107),
    rarity_common=(196, 124, 56),
    rarity_uncommon=(200, 210, 226),
    rarity_rare=(240, 192, 96),
    rarity_legendary=(192, 130, 255),
    icon_credits=(110, 200, 240),
    icon_ducats=(230, 180, 80),
    icon_platinum=(201, 216, 240),
)

LIGHT = Palette(
    canvas=(226, 231, 240),
    surface=(255, 255, 255),
    surface_alt=(237, 241, 248),
    border=(207, 215, 228),
    text=(18, 22, 31),
    text_muted=(84, 94, 114),
    text_dim=(120, 129, 143),
    gold=(138, 94, 16),
    blue=(36, 88, 184),
    green=(24, 122, 76),
    amber=(138, 94, 16),
    red=(176, 48, 62),
    # 亮色下铜与金天然接近，靠「饱和度」拉开：常见低饱和哑光、稀有满饱和琥珀
    rarity_common=(122, 96, 72),
    rarity_uncommon=(74, 94, 120),
    rarity_rare=(170, 118, 0),
    rarity_legendary=(106, 48, 168),
    icon_credits=(24, 110, 158),
    icon_ducats=(150, 102, 0),
    icon_platinum=(92, 112, 146),
)


@dataclass(frozen=True)
class Theme:
    """主题 = 名字 + 色板。"""

    name: str
    palette: Palette


THEMES: dict[str, Theme] = {
    "dark": Theme("dark", DARK),
    "light": Theme("light", LIGHT),
}

DEFAULT_THEME = "dark"


def get_theme(name: str | None = None) -> Theme:
    """按名字取主题，未知值回退默认。"""
    return THEMES.get((name or DEFAULT_THEME).lower(), THEMES[DEFAULT_THEME])


# ---------------------------------------------------------------- 字体
_FONT_DIR = Path(__file__).parent / "fonts"

#: 字体优先级：``(文件名, ttc 索引, 是否可变字体)``。
#: 项目自带思源宋体（Bold），只有它缺失时才退回系统无衬线。
_FONT_CANDIDATES: tuple[tuple[str, int, bool], ...] = (
    ("SourceHanSerifCN-Bold.ttf", 0, False),
    ("NotoSansSC-VF.ttf", 0, True),
    ("msyh.ttc", 0, False),
    ("Deng.ttf", 0, False),
)

_FONT_SEARCH_DIRS: tuple[Path, ...] = (_FONT_DIR, Path("C:/Windows/Fonts"))
_font_cache: dict[tuple[str, int, int], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}
_font_pick: tuple[str, int, bool] | None = None


def _resolve_font() -> tuple[str, int, bool] | None:
    """按优先级找一个可用的中文字体。"""
    global _font_pick
    if _font_pick is not None:
        return _font_pick
    for filename, index, variable in _FONT_CANDIDATES:
        for directory in _FONT_SEARCH_DIRS:
            candidate = directory / filename
            if candidate.exists():
                _font_pick = (str(candidate), index, variable)
                return _font_pick
    return None


def font(
    size_key: str, bold: bool = False
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """按字阶取字体（带缓存）。

    Args:
        size_key: ``FONT`` 的键（xs/sm/base/md/lg/xl/2xl）。
        bold: 是否用粗体。可变字体按权重轴切换（400 / 700）。
    """
    size = FONT[size_key]
    weight = 700 if bold else 400
    picked = _resolve_font()
    if picked is None:
        return ImageFont.load_default()

    path, index, variable = picked
    cache_key = (path, size, weight if variable else 0)
    if cache_key not in _font_cache:
        face = ImageFont.truetype(path, size, index=index)
        if variable:
            try:
                face.set_variation_by_axes([weight])
            except Exception:
                pass
        _font_cache[cache_key] = face
    return _font_cache[cache_key]


#: 图标 → 调色板字段。图标身份（青 / 金 / 银蓝）固定，明暗只调明度。
_ICON_FIELD: dict[str, str] = {
    "\ue306": "icon_credits",   # CREDITS
    "\ue305": "icon_ducats",    # DUCATS
    "\ue309": "icon_platinum",  # PLATINUM
}


def _relative_luma(rgb: RGB) -> float:
    """WCAG 相对亮度。"""
    def channel(value: int) -> float:
        c = value / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: RGB, b: RGB) -> float:
    """两色的对比度（1~21）。"""
    high, low = sorted((_relative_luma(a), _relative_luma(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


#: 合法十六进制色值：``#RRGGBB`` 或 ``RRGGBB``（3 位缩写历史上就不支持，
#: ``semantic_color`` 把 ``#000`` 列入「未配置色」，无需在此放宽）。
_HEX_COLOR_RE = re.compile(r"^#?[0-9A-Fa-f]{6}$")


def parse_hex(value: object) -> RGB | None:
    """``#RRGGBB`` → RGB；非法输入返回 ``None``（调用方决定兜底色）。

    游戏数据里的色值无法在编译期发现（任务类型、派系、稀有度），
    这里只做校验不抛异常——一个错别字不值得让群里的图崩掉。
    """
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not _HEX_COLOR_RE.match(text):
        return None
    text = text.lstrip("#")
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)


def hex_to_rgb(value: object, fallback: RGB = (0, 0, 0)) -> RGB:
    """``#RRGGBB`` → RGB；非法输入（``#FFF`` / ``#GGGGGG`` / 空串 / ``None``）
    回退 ``fallback``，不抛异常。"""
    return parse_hex(value) or fallback


def adapt_color(value: str | RGB, theme: Theme, target: float = 4.5) -> RGB:
    """把语义色适配到当前主题的底色。

    游戏内原色（任务类型、元素、稀有度）是按深色背景设计的，直接放到白底上
    对比度常低于 2:1。这里保持色相与饱和度，只朝「远离底色」的方向调明度，
    直到达到 ``target`` 对比度；达标则原样返回。

    Args:
        value: ``#RRGGBB`` 或 RGB 三元组。
        theme: 目标主题（用其 ``surface`` 作底色）。
        target: 目标对比度，默认 4.5（AA 正文）。
    """
    rgb = parse_hex(value) if isinstance(value, str) else value
    if rgb is None:  # 非法色值：退回中性色，不让脏数据打断渲染
        return theme.palette.text_muted
    background = theme.palette.surface
    if contrast(rgb, background) >= target:
        return rgb

    import colorsys

    hue, lightness, saturation = colorsys.rgb_to_hls(*(v / 255 for v in rgb))
    away = -1 if _relative_luma(rgb) < _relative_luma(background) else 1

    best = rgb
    for step in range(1, 101):
        adjusted = colorsys.hls_to_rgb(hue, min(1.0, max(0.0, lightness + away * step * 0.01)), saturation)
        best = tuple(round(v * 255) for v in adjusted)  # type: ignore[assignment]
        if contrast(best, background) >= target:
            return best
    return best


def icon_color(icon: str, palette: Palette) -> RGB:
    """图标颜色；未登记的图标退回次要文字色。"""
    field = _ICON_FIELD.get(icon)
    return getattr(palette, field) if field else palette.text_muted


#: 游戏数据里表示「没有颜色」的取值。
_UNSET_COLORS = frozenset({"", "#000", "#000000", "none"})


def semantic_color(
    value: str | RGB | None,
    theme: Theme,
    fallback: RGB,
    target: float = 4.5,
) -> RGB:
    """游戏语义色 → 当前主题下可用的颜色；「未配置色」退回 ``fallback``。

    与 :func:`adapt_color` 的区别：这里把 ``#000000`` / 空值当作「没有颜色」。
    游戏数据常用纯黑表示未配置（如 ``MT_DEFAULT``、``FC_NONE``），
    而 ``adapt_color`` 在深色主题上会让纯黑继续变暗，最终完全看不见。

    Args:
        value: ``#RRGGBB`` / RGB / ``None``。
        theme: 目标主题。
        fallback: 未配置时的替代色（通常 ``palette.text_muted``）。
        target: 目标对比度，透传给 :func:`adapt_color`。

    Returns:
        适配后的 RGB。
    """
    if isinstance(value, str):
        if value.strip().lower() in _UNSET_COLORS:
            return fallback
        if parse_hex(value) is None:  # 非法色值同样按「没有颜色」处理
            return fallback
        return adapt_color(value, theme, target)
    if (
        isinstance(value, tuple)
        and len(value) == 3
        and all(isinstance(v, int) for v in value)
    ):
        if tuple(value) == (0, 0, 0):
            return fallback
        return adapt_color(value, theme, target)
    return fallback  # 其余类型（int / 长度不对的 tuple 等）按「没有颜色」处理


def icon_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Warframe 图标字体。"""
    from .font_manager import FontManager

    return FontManager.get_wf_icon_font(size)
