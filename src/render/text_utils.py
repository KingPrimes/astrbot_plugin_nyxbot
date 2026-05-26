"""Text utilities / 文本工具模块

提供静态工具方法，用于处理文本相关的功能，对应 Java TextUtils.java。

功能：
- 居中坐标计算 (calculateCenterX / calculateCenterXY)
- 自动换行 (wrapText)
- 多行文本高度计算
- 带背景框文本绘制
- 带渐变背景框文本绘制
- 带阴影文本绘制
- 高级文本绘制（整合所有样式）
"""
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from PIL import ImageDraw, ImageFont

from .graphics_utils import draw_rounded_rect

if TYPE_CHECKING:
    from PIL import Image


# ============================================================================
# 对齐枚举
# ============================================================================

class TextAlign(Enum):
    """文本对齐方式 — 对应 Java ImageCombiner.Align。"""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


# ============================================================================
# 居中坐标计算
# ============================================================================

def calc_center_x(
    draw: ImageDraw.ImageDraw,
    text: str,
    canvas_width: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None,
    x_offset: int = 0,
) -> int:
    """计算单行文本在指定宽度画布上的水平居中 X 坐标。

    对应 Java TextUtils.calculateCenterX()。

    Args:
        draw: ImageDraw 对象（用于 textbbox 测量）。
        text: 待居中的单行文本。
        canvas_width: 画布宽度（像素）。
        font: 字体（None 时使用 draw 默认字体）。
        x_offset: X 轴偏移量。

    Returns:
        文本水平居中时的左边缘 X 坐标。
    """
    if not text:
        return 0
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = int(bbox[2] - bbox[0])
    return (canvas_width - text_width) // 2 + x_offset


def calc_center_xy(
    draw: ImageDraw.ImageDraw,
    text: str,
    canvas_width: int,
    canvas_height: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None,
    x_offset: int = 0,
    y_offset: int = 0,
) -> tuple[int, int]:
    """计算单行文字完全居中（X、Y 轴）的坐标。

    对应 Java TextUtils.calculateCenterXY()。

    Args:
        draw: ImageDraw 对象。
        text: 待居中的单行文本。
        canvas_width: 画布宽度。
        canvas_height: 画布高度。
        font: 字体。
        x_offset: X 轴偏移量。
        y_offset: Y 轴偏移量。

    Returns:
        (x, y) 坐标。
    """
    if not text:
        return (0, 0)

    x = calc_center_x(draw, text, canvas_width, font, x_offset)

    bbox = draw.textbbox((0, 0), text, font=font)
    text_height = int(bbox[3] - bbox[1])
    y = (canvas_height - text_height) // 2 + y_offset

    # 补偿基线偏移
    ascent = _get_ascent(draw, font)
    y += ascent // 2

    return (x, y)


def _get_ascent(
    draw: ImageDraw.ImageDraw,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None,
) -> int:
    """估算字体 ascent 值（Pillow 不直接暴露 metrics）。"""
    if font is None:
        return 0
    try:
        bbox = draw.textbbox((0, 0), "Ay", font=font)
        # ascent ≈ 大写字母顶部偏移的绝对值
        return int(abs(bbox[1]))
    except Exception:
        return 0


def get_text_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None,
) -> int:
    """获取文本绘制宽度。

    对应 Java TextUtils 中的 stringWidth 调用。

    Args:
        draw: ImageDraw 对象。
        text: 文本内容。
        font: 字体。

    Returns:
        文本宽度（像素）。
    """
    bbox = draw.textbbox((0, 0), text, font=font)
    return int(bbox[2] - bbox[0])


# ============================================================================
# 自动换行
# ============================================================================

def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None,
) -> list[str]:
    """根据指定的最大宽度对文本进行自动换行处理。

    对应 Java TextUtils.wrapText()。
    使用逐字符贪心算法，适合 CJK 文本（每个字都可以是断点）。

    Args:
        draw: ImageDraw 对象。
        text: 需要换行处理的文本。
        max_width: 每行最大宽度。
        font: 字体。

    Returns:
        按宽度换行后的文本行列表。
    """
    if not text or max_width <= 0:
        return [text or ""]

    lines: list[str] = []
    current_line = ""

    for ch in text:
        test_line = current_line + ch
        if get_text_width(draw, test_line, font) <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = ch

    if current_line:
        lines.append(current_line)

    return lines if lines else [text]


# ============================================================================
# 文本高度计算
# ============================================================================

def calc_line_height(
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None,
) -> int:
    """估算单行文本高度。

    Args:
        font: 字体（None 时使用默认估算值）。

    Returns:
        行高（像素）。
    """
    if font is None:
        return 20
    # 使用 "Ay" 的高度作为行高估算（含 ascent + descent）
    temp_img = _make_temp_image()
    temp_draw = ImageDraw.Draw(temp_img)
    bbox = temp_draw.textbbox((0, 0), "Ay", font=font)
    return int(bbox[3] - bbox[1])


def calc_multiline_height(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    line_height: int,
    spacing: int = 0,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None,
) -> int:
    """计算多行文本总高度（含行间距）。

    对应 Java TextUtils.calculateMultilineHeight()。

    Args:
        draw: ImageDraw 对象。
        lines: 文本行列表。
        line_height: 单行高度。
        spacing: 行间距。
        font: 字体。

    Returns:
        多行文本总高度。
    """
    if not lines:
        return 0

    if line_height <= 0:
        line_height = calc_line_height(font)
    return len(lines) * line_height + (len(lines) - 1) * spacing


def calc_wrapped_text_height(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    line_height: int,
    spacing: int = 0,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None,
) -> int:
    """计算自动换行后文本的总高度。

    对应 Java TextUtils.calculateWrappedTextHeight()。

    Args:
        draw: ImageDraw 对象。
        text: 需要计算高度的文本。
        max_width: 最大宽度。
        line_height: 单行高度。
        spacing: 行间距。
        font: 字体。

    Returns:
        自动换行后文本总高度。
    """
    if not text or max_width <= 0:
        return 0
    lines = wrap_text(draw, text, max_width, font)
    return calc_multiline_height(draw, lines, line_height, spacing, font)


# ============================================================================
# 基础文本绘制
# ============================================================================

def draw_text_with_background(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    text_color: tuple[int, int, int],
    bg_color: tuple[int, int, int] | None = None,
    border_color: tuple[int, int, int] | None = None,
    corner_radius: int = 4,
    padding: int = 4,
) -> None:
    """绘制带背景框的单行文本。

    对应 Java TextUtils.drawTextWithBackground()。

    Args:
        draw: ImageDraw 对象。
        text: 文本内容。
        x: 文本 X 坐标（基线位置）。
        y: 文本 Y 坐标（基线位置）。
        font: 字体。
        text_color: 文本颜色。
        bg_color: 背景颜色（None 不绘制）。
        border_color: 边框颜色（None 不绘制）。
        corner_radius: 圆角半径。
        padding: 内边距。
    """
    if not text:
        return

    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = int(bbox[2] - bbox[0])
    text_height = int(bbox[3] - bbox[1])
    # 文本基线偏移
    ascent = int(abs(bbox[1])) if bbox[1] < 0 else 0

    bg_x1 = x - padding
    bg_y1 = y - ascent - padding
    bg_x2 = x + text_width + padding
    bg_y2 = y + (text_height - ascent) + padding

    # 1. 绘制背景
    if bg_color is not None:
        draw_rounded_rect(
            draw,
            (bg_x1, bg_y1, bg_x2, bg_y2),
            radius=corner_radius,
            fill=bg_color,
        )

    # 2. 绘制边框
    if border_color is not None:
        draw_rounded_rect(
            draw,
            (bg_x1, bg_y1, bg_x2, bg_y2),
            radius=corner_radius,
            outline=border_color,
            width=1,
        )

    # 3. 绘制文字
    draw.text((x, y), text, fill=text_color, font=font)


def draw_text_with_shadow(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    text_color: tuple[int, int, int],
    shadow_color: tuple[int, int, int],
    shadow_offset_x: int = 1,
    shadow_offset_y: int = 1,
) -> None:
    """绘制带阴影的文字。

    对应 Java TextUtils.drawTextWithShadow()。

    Args:
        draw: ImageDraw 对象。
        text: 文本内容。
        x: 文本 X 坐标。
        y: 文本 Y 坐标。
        font: 字体。
        text_color: 文本颜色。
        shadow_color: 阴影颜色。
        shadow_offset_x: 阴影 X 偏移。
        shadow_offset_y: 阴影 Y 偏移。
    """
    if not text:
        return

    # 1. 先画阴影
    draw.text(
        (x + shadow_offset_x, y + shadow_offset_y),
        text,
        fill=shadow_color,
        font=font,
    )

    # 2. 再画文字
    draw.text((x, y), text, fill=text_color, font=font)


# ============================================================================
# 高级文本绘制（整合所有样式）
# ============================================================================

def draw_advanced_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    canvas_width: int,
    canvas_height: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    text_color: tuple[int, int, int],
    align: TextAlign = TextAlign.LEFT,
    is_vertical_center: bool = False,
    bg_color: tuple[int, int, int] | None = None,
    gradient_start: tuple[int, int, int] | None = None,
    gradient_end: tuple[int, int, int] | None = None,
    is_vertical_gradient: bool = False,
    border_color: tuple[int, int, int] | None = None,
    corner_radius: int = 8,
    padding: int = 10,
    shadow_color: tuple[int, int, int] | None = None,
    shadow_offset_x: int = 1,
    shadow_offset_y: int = 1,
    line_spacing: int = 4,
) -> tuple[int, int]:
    """高级多行文本绘制：自动换行 + 背景/渐变 + 边框 + 圆角 + 阴影 + 对齐。

    对应 Java TextUtils.drawAdvancedText()。

    Args:
        draw: ImageDraw 对象。
        text: 待绘制的文本内容。
        max_width: 单行最大宽度。
        canvas_width: 画布宽度。
        canvas_height: 画布高度。
        font: 字体。
        text_color: 文字颜色。
        align: 水平对齐方式。
        is_vertical_center: 是否垂直居中。
        bg_color: 背景颜色。
        gradient_start: 渐变起始颜色。
        gradient_end: 渐变结束颜色。
        is_vertical_gradient: True=纵向渐变，False=横向渐变。
        border_color: 边框颜色。
        corner_radius: 圆角半径。
        padding: 内边距。
        shadow_color: 阴影颜色。
        shadow_offset_x: 阴影 X 偏移。
        shadow_offset_y: 阴影 Y 偏移。
        line_spacing: 行间距。

    Returns:
        (实际占用宽度, 实际占用高度) 元组。
    """
    if not text:
        return (0, 0)

    # 1. 自动换行
    lines = wrap_text(draw, text, max_width, font)
    if not lines:
        return (0, 0)

    # 2. 计算文本总宽高
    line_height = calc_line_height(font)
    total_text_width = max(get_text_width(draw, line, font) for line in lines)
    total_text_height = calc_multiline_height(draw, lines, line_height, line_spacing, font)

    # 3. 计算起始位置
    start_x = padding
    start_y = padding

    # 水平对齐
    if align == TextAlign.CENTER:
        start_x = (canvas_width - total_text_width) // 2
    elif align == TextAlign.RIGHT:
        start_x = canvas_width - total_text_width - padding

    # 垂直居中
    if is_vertical_center:
        content_total_height = total_text_height + 2 * padding
        start_y = (canvas_height - content_total_height) // 2 + padding

    ascent = _get_ascent(draw, font)

    # 4. 绘制背景（纯色或渐变）
    bg_x = start_x - padding
    bg_y = start_y - padding
    bg_w = total_text_width + 2 * padding
    bg_h = total_text_height + 2 * padding

    if gradient_start is not None and gradient_end is not None:
        # 渐变背景
        from .graphics_utils import create_gradient_background

        gradient_img = create_gradient_background(
            bg_w, bg_h,
            gradient_start, gradient_end,
            vertical=is_vertical_gradient,
        )
        # 将渐变图粘贴到目标 draw 对应的图像上
        draw._image.paste(gradient_img, (bg_x, bg_y), gradient_img)
    elif bg_color is not None:
        draw_rounded_rect(
            draw,
            (bg_x, bg_y, bg_x + bg_w, bg_y + bg_h),
            radius=corner_radius,
            fill=bg_color,
        )

    # 5. 绘制边框
    if border_color is not None:
        draw_rounded_rect(
            draw,
            (bg_x, bg_y, bg_x + bg_w, bg_y + bg_h),
            radius=corner_radius,
            outline=border_color,
            width=1,
        )

    # 6. 绘制每行文字
    current_y = start_y + ascent
    for line in lines:
        line_x = start_x

        # 单行水平对齐
        if align == TextAlign.CENTER:
            line_x = (canvas_width - get_text_width(draw, line, font)) // 2
        elif align == TextAlign.RIGHT:
            line_x = canvas_width - get_text_width(draw, line, font) - padding

        # 阴影
        if shadow_color is not None:
            draw_text_with_shadow(
                draw, line, line_x, current_y, font,
                text_color, shadow_color,
                shadow_offset_x, shadow_offset_y,
            )
        else:
            draw.text((line_x, current_y), line, fill=text_color, font=font)

        current_y += line_height + line_spacing

    return (bg_w, bg_h)


# ============================================================================
# 内部工具
# ============================================================================

def _make_temp_image() -> Image.Image:
    """创建一个 1x1 的临时图像用于字体度量。"""
    from PIL import Image  # noqa: PLC0415
    return Image.new("RGBA", (1, 1))
