"""Render package / 图片渲染包"""
from .card_renderer import CardRenderer
from .composer import ImageComposer
from .draw_constant import DrawConstant, ThemeColor, hex_to_rgb, lerp_color, rgb_to_hex
from .font_manager import FontManager
from .graphics_utils import (
    create_gradient_background,
    create_rounded_image,
    draw_circle,
    draw_horizontal_divider,
    draw_rounded_rect,
)
from .image_combiner import ImageCombiner, OutputFormat
from .text_utils import (
    TextAlign,
    calc_center_x,
    calc_center_xy,
    calc_line_height,
    calc_multiline_height,
    calc_wrapped_text_height,
    draw_advanced_text,
    draw_text_with_background,
    draw_text_with_shadow,
    get_text_width,
    wrap_text,
)

__all__ = [
    # 主渲染器
    "CardRenderer",
    # 合成器（简单模式）
    "ImageComposer",
    # 建造者模式组合器
    "ImageCombiner",
    "OutputFormat",
    # 字体管理
    "FontManager",
    # 常量
    "DrawConstant",
    "ThemeColor",
    "hex_to_rgb",
    "rgb_to_hex",
    "lerp_color",
    # 图形工具
    "create_gradient_background",
    "create_rounded_image",
    "draw_circle",
    "draw_horizontal_divider",
    "draw_rounded_rect",
    # 文本工具
    "TextAlign",
    "calc_center_x",
    "calc_center_xy",
    "calc_line_height",
    "calc_multiline_height",
    "calc_wrapped_text_height",
    "draw_advanced_text",
    "draw_text_with_background",
    "draw_text_with_shadow",
    "get_text_width",
    "wrap_text",
]
