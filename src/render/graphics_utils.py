"""Graphics utilities / 图形工具模块

提供高层图形操作工具，对应 Java GraphicsUtils.java。

功能：
- 高质量渲染配置（Pillow 对应项）
- 圆角矩形图像
- 渐变背景
- 形状绘制
"""
from __future__ import annotations

from PIL import Image, ImageDraw


def create_rounded_image(
    image: Image.Image,
    corner_radius: int,
) -> Image.Image:
    """将原始图片处理为圆角矩形效果。

    对应 Java GraphicsUtils.createRoundedImage()。

    Args:
        image: 原始图片对象。
        corner_radius: 圆角半径（像素）。

    Returns:
        带圆角的新 Image 对象，RGBA 模式。
    """
    if corner_radius <= 0:
        return image.copy()

    # 确保图像为 RGBA 模式
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    # 创建圆角遮罩
    mask = Image.new("L", image.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(
        [(0, 0), (image.width - 1, image.height - 1)],
        radius=corner_radius,
        fill=255,
    )

    # 应用遮罩
    rounded = Image.new("RGBA", image.size, (0, 0, 0, 0))
    rounded.paste(image, (0, 0), mask)

    return rounded


def create_gradient_background(
    width: int,
    height: int,
    start_color: tuple[int, int, int],
    end_color: tuple[int, int, int],
    vertical: bool = False,
) -> Image.Image:
    """创建指定尺寸和渐变效果的背景图片。

    对应 Java GraphicsUtils.createGradientBackground()。

    Args:
        width: 背景宽度（像素）。
        height: 背景高度（像素）。
        start_color: 渐变起始颜色 (R, G, B)。
        end_color: 渐变结束颜色 (R, G, B)。
        vertical: True=垂直渐变，False=水平渐变。

    Returns:
        带渐变背景的新 Image 对象，RGBA 模式。
    """
    image = Image.new("RGBA", (width, height))
    pixels = image.load()

    if pixels is None:
        # 极端回退：逐像素使用 putpixel
        for y in range(height):
            for x in range(width):
                t = y / max(height - 1, 1) if vertical else x / max(width - 1, 1)
                r = int(start_color[0] + (end_color[0] - start_color[0]) * t)
                g = int(start_color[1] + (end_color[1] - start_color[1]) * t)
                b = int(start_color[2] + (end_color[2] - start_color[2]) * t)
                image.putpixel((x, y), (r, g, b, 255))
        return image

    for y in range(height):
        for x in range(width):
            if vertical:
                t = y / max(height - 1, 1)
            else:
                t = x / max(width - 1, 1)

            r = int(start_color[0] + (end_color[0] - start_color[0]) * t)
            g = int(start_color[1] + (end_color[1] - start_color[1]) * t)
            b = int(start_color[2] + (end_color[2] - start_color[2]) * t)
            pixels[x, y] = (r, g, b, 255)

    return image


def draw_rounded_rect(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    radius: int = 8,
    fill: tuple[int, int, int] | None = None,
    outline: tuple[int, int, int] | None = None,
    width: int = 1,
) -> None:
    """绘制圆角矩形（Pillow 内置方法的便捷封装）。

    Args:
        draw: ImageDraw 对象。
        xy: (x1, y1, x2, y2) 矩形坐标。
        radius: 圆角半径。
        fill: 填充颜色。
        outline: 边框颜色。
        width: 边框宽度。
    """
    draw.rounded_rectangle(
        xy,
        radius=radius,
        fill=fill,
        outline=outline,
        width=width,
    )


def draw_circle(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    radius: int,
    fill: tuple[int, int, int] | None = None,
    outline: tuple[int, int, int] | None = None,
    width: int = 1,
) -> None:
    """绘制圆形。

    Args:
        draw: ImageDraw 对象。
        center: (cx, cy) 圆心坐标。
        radius: 半径。
        fill: 填充颜色。
        outline: 边框颜色。
        width: 边框宽度。
    """
    cx, cy = center
    bbox = [
        (cx - radius, cy - radius),
        (cx + radius, cy + radius),
    ]
    draw.ellipse(bbox, fill=fill, outline=outline, width=width)


def draw_horizontal_divider(
    draw: ImageDraw.ImageDraw,
    y: int,
    x1: int,
    x2: int,
    color: tuple[int, int, int],
    width: int = 2,
) -> None:
    """绘制水平分割线。

    Args:
        draw: ImageDraw 对象。
        y: Y 坐标。
        x1: 起点 X。
        x2: 终点 X。
        color: 线条颜色。
        width: 线条宽度。
    """
    draw.line([(x1, y), (x2, y)], fill=color, width=width)
