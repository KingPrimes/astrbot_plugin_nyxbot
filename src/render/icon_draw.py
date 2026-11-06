"""Icon drawing / 图标绘制层

把 :mod:`icon_registry` 里的图标画到画布上。本模块**不持有任何码位或色值**，
只负责「按语义 token 取图 → 按主题取色 → 落到坐标」。

字体已度量归一（墨迹盒 896×896 居中于 em 方框、advance 1024，见
``icon_registry.INK_BOX`` / ``INK_CENTER``），所以：

- **字号 = 图标边长**：``size=24`` 表示图标占 24×24，墨迹居中，无需运行时缩放；
- **图标字号 = 文字字号**：墨迹高度 0.875em，与中文字面高度接近，并排时天然同高；
- 不再需要 bbox 补偿，绘制坐标就是方框左上角。

用法::

    from .icon_draw import draw_icon, draw_icon_label

    draw_icon(cb, "heat", x, y, 24, theme)
    draw_icon_label(cb, "heat", x, y, 24, theme, text="火焰伤害")
"""
from __future__ import annotations

import colorsys

from .design import RGB, Theme, icon_color, icon_font
from .theme import current_theme
from .icon_registry import ICONS, NEUTRAL_COLOR, IconEntry, validate_icon_size

#: 图标与右侧文字的间距（相对边长的比例）。
_LABEL_GAP_RATIO = 0.25

#: 语义色在主题底色上的目标对比度（AA 正文标准）。
_TARGET_CONTRAST = 4.5

_TINT_CACHE: dict[tuple[str, str], RGB] = {}


def _to_rgb(value: str) -> RGB:
    text = value.lstrip("#")
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)


def _luma(rgb: RGB) -> float:
    def channel(value: int) -> float:
        c = value / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a: RGB, b: RGB) -> float:
    high, low = sorted((_luma(a), _luma(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _toward_contrast(rgb: RGB, background: RGB) -> RGB:
    """保持色相，只调明度，直到与底色对比度达标。"""
    if _contrast(rgb, background) >= _TARGET_CONTRAST:
        return rgb

    hue, lightness, saturation = colorsys.rgb_to_hls(*(v / 255 for v in rgb))
    away = -1 if _luma(rgb) < _luma(background) else 1  # 朝远离底色的方向走

    best = rgb
    for step in range(1, 101):
        candidate_lightness = min(1.0, max(0.0, lightness + away * step * 0.01))
        candidate = colorsys.hls_to_rgb(hue, candidate_lightness, saturation)
        best = tuple(round(v * 255) for v in candidate)  # type: ignore[assignment]
        if _contrast(best, background) >= _TARGET_CONTRAST:
            return best
    return best


def icon_tint(entry: IconEntry, theme: Theme) -> RGB:
    """图标颜色：注册表语义色 + 主题适配。

    语义色是游戏内原色，在亮色底上常常不足 4.5:1（如腐蚀 #B2CA01 白底仅 1.85:1），
    这里保持色相压/提明度到可读；``NEUTRAL_COLOR`` 表示「由主题决定」，
    交给 :func:`design.icon_color` 按调色板取（货币有专属身份色）。
    """
    if entry.color == NEUTRAL_COLOR:
        return icon_color(entry.char, theme.palette)

    key = (entry.color, theme.name)
    if key not in _TINT_CACHE:
        _TINT_CACHE[key] = _toward_contrast(_to_rgb(entry.color), theme.palette.surface)
    return _TINT_CACHE[key]


def draw_icon(
    cb,
    token: str,
    x: int,
    y: int,
    size: int,
    theme: Theme | None = None,
    *,
    color: RGB | None = None,
) -> int:
    """在 ``(x, y)`` 为左上角的 ``size×size`` 方框内画图标。

    Args:
        cb: ``ImageCombiner``。
        token: 注册表 token（``"heat"`` / ``"U+E607"`` / ``0xE607`` 均可）。
        x, y: 方框左上角。
        size: 方框边长，同时就是字号。
        theme: 主题，决定默认颜色。
        color: 显式覆盖颜色。

    Returns:
        占用的宽度（等于 ``size``）。
    """
    entry = ICONS.require(token)
    tint = color or icon_tint(entry, theme or current_theme())
    cb.set_color(tint).set_font(icon_font(validate_icon_size(size)))
    cb.add_text(entry.char, x, y)
    return size


def draw_icon_label(
    cb,
    token: str,
    x: int,
    y: int,
    size: int,
    theme: Theme | None = None,
    *,
    text: str | None = None,
    color: RGB | None = None,
    text_size: int | None = None,
) -> int:
    """画「图标 + 文字」，两者按墨迹垂直居中对齐。

    Args:
        text: 文案，默认取注册表里的展示名。
        text_size: 文字字号，默认与图标同字号（字体归一后两者视觉同高）。

    Returns:
        组合总宽度（图标 + 间距 + 文字）。
    """
    from .font_manager import FontManager

    entry = ICONS.require(token)
    resolved = theme or current_theme()
    label = text if text is not None else entry.name
    tint = color or icon_tint(entry, resolved)

    width = draw_icon(cb, token, x, y, size, resolved, color=tint)
    gap = round(size * _LABEL_GAP_RATIO)

    if label:
        text_font = FontManager.get_text_font(text_size or size)
        bbox = text_font.getbbox(label)
        text_y = y + (size - (bbox[3] - bbox[1])) / 2 - bbox[1]
        cb.set_color(tint).set_font(text_font)
        cb.add_text(label, x + width + gap, round(text_y))
        width += gap + cb.get_string_width(label)

    return width
