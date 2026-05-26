"""Image combiner / 图片组合器（建造者模式）

对应 Java ImageCombiner.java。
提供一站式图像构建能力，整合画布管理、基础图形绘制、文本处理和最终图像输出。

用法::

    combiner = ImageCombiner(800, 400)
    combiner.set_color(ThemeColor.TEXT_PRIMARY)
    combiner.set_font(font_text)
    combiner.add_centered_text("标题", y=60)
    img_bytes = combiner.combine()
"""
from __future__ import annotations

import io
from enum import Enum
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from .draw_constant import DrawConstant, LayoutConstants, ThemeColor
from .font_manager import FontManager
from .graphics_utils import (
    create_rounded_image,
    draw_rounded_rect,
)
from .text_utils import (
    TextAlign,
    calc_center_x,
    calc_center_xy,
    calc_line_height,
    draw_advanced_text,
    draw_text_with_background,
    draw_text_with_shadow,
    get_text_width,
    wrap_text,
)

if TYPE_CHECKING:
    pass


class OutputFormat(Enum):
    """图片输出格式 — 对应 Java ImageCombiner.OutputFormat。"""
    PNG = "PNG"
    JPG = "JPEG"


class ImageCombiner:
    """图片绘制组合器（建造者模式实现）。

    对应 Java ImageCombiner。
    提供链式调用 API，整合画布管理、图形绘制、文本处理和最终输出。
    """

    def __init__(
        self,
        width: int,
        height: int,
        bg_color: tuple[int, int, int] | None = None,
        output_format: OutputFormat = OutputFormat.PNG,
    ) -> None:
        """创建图像合成器实例。

        Args:
            width: 画布宽度（像素）。
            height: 画布高度（像素）。
            bg_color: 背景颜色，None 表示透明。
            output_format: 输出格式。
        """
        if width <= 0 or height <= 0:
            raise ValueError(f"宽高需>0，当前: {width}x{height}")

        self._width = width
        self._height = height
        self._format = output_format

        # 画布：使用 RGBA 支持透明度
        self._image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        self._draw = ImageDraw.Draw(self._image)

        # 当前状态
        self._current_font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None
        self._current_color: tuple[int, int, int] = ThemeColor.TEXT_PRIMARY

        # 默认加载文本字体
        try:
            self._default_font = FontManager.get_text_font(20)
        except Exception:
            self._default_font = ImageFont.load_default()

        # 填充背景
        if bg_color is not None:
            self._draw.rectangle(
                [(0, 0), (width, height)],
                fill=bg_color,
            )

    # ========================================================================
    # 属性访问
    # ========================================================================

    @property
    def image(self) -> Image.Image:
        """获取当前画布（PIL Image）。"""
        return self._image

    @property
    def draw(self) -> ImageDraw.ImageDraw:
        """获取当前 ImageDraw 对象。"""
        return self._draw

    @property
    def width(self) -> int:
        """画布宽度。"""
        return self._width

    @property
    def height(self) -> int:
        """画布高度。"""
        return self._height

    # ========================================================================
    # 状态设置（链式调用）
    # ========================================================================

    def set_color(self, color: tuple[int, int, int]) -> ImageCombiner:
        """设置当前绘图颜色。

        Args:
            color: RGB 颜色元组。

        Returns:
            self，支持链式调用。
        """
        self._current_color = color
        return self

    def set_font(self, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> ImageCombiner:
        """设置当前字体。

        Args:
            font: 字体对象。

        Returns:
            self，支持链式调用。
        """
        self._current_font = font
        return self

    @property
    def current_font(self) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """获取当前字体（回退到默认字体）。"""
        return self._current_font or self._default_font

    @property
    def current_color(self) -> tuple[int, int, int]:
        """获取当前颜色。"""
        return self._current_color

    # ========================================================================
    # 基础图形
    # ========================================================================

    def fill_rect(self, x: int, y: int, width: int, height: int) -> ImageCombiner:
        """填充矩形区域。

        Args:
            x, y: 左上角坐标。
            width, height: 宽高。

        Returns:
            self，支持链式调用。
        """
        self._draw.rectangle(
            [(x, y), (x + width, y + height)],
            fill=self._current_color,
        )
        return self

    def draw_rounded_rect(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        radius: int = 8,
        fill: tuple[int, int, int] | None = None,
        outline: tuple[int, int, int] | None = None,
        stroke_width: int = 1,
    ) -> ImageCombiner:
        """绘制圆角矩形。

        Args:
            x, y: 左上角坐标。
            width, height: 宽高。
            radius: 圆角半径。
            fill: 填充颜色（None 使用当前颜色）。
            outline: 边框颜色。
            stroke_width: 边框宽度。

        Returns:
            self，支持链式调用。
        """
        draw_rounded_rect(
            self._draw,
            (x, y, x + width, y + height),
            radius=radius,
            fill=fill if fill is not None else self._current_color,
            outline=outline,
            width=stroke_width,
        )
        return self

    def draw_line(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        width: int = 1,
    ) -> ImageCombiner:
        """绘制直线。

        Args:
            x1, y1: 起点。
            x2, y2: 终点。
            width: 线宽。

        Returns:
            self，支持链式调用。
        """
        self._draw.line(
            [(x1, y1), (x2, y2)],
            fill=self._current_color,
            width=width,
        )
        return self

    # ========================================================================
    # 图像绘制
    # ========================================================================

    def draw_image(
        self,
        img: Image.Image,
        x: int,
        y: int,
        width: int | None = None,
        height: int | None = None,
    ) -> ImageCombiner:
        """在指定位置绘制图像。

        Args:
            img: 要绘制的图像。
            x, y: 绘制位置。
            width, height: 目标尺寸（None 保持原始尺寸）。

        Returns:
            self，支持链式调用。
        """
        if width is not None and height is not None:
            img = img.resize((width, height), Image.Resampling.LANCZOS)
        self._image.paste(img, (x, y), img if img.mode == "RGBA" else None)
        return self

    def add_rounded_image(
        self,
        img: Image.Image,
        x: int,
        y: int,
        corner_radius: int,
    ) -> ImageCombiner:
        """绘制带圆角的图像。

        对应 Java ImageCombiner.addRoundedImage()。

        Args:
            img: 源图像。
            x, y: 位置。
            corner_radius: 圆角半径。

        Returns:
            self，支持链式调用。
        """
        if img is None or corner_radius < 0:
            return self
        rounded = create_rounded_image(img, corner_radius)
        self._image.paste(rounded, (x, y), rounded)
        return self

    # ========================================================================
    # 文本绘制
    # ========================================================================

    def add_text(self, text: str, x: int, y: int) -> ImageCombiner:
        """绘制简单文本（使用当前字体和颜色）。

        对应 Java ImageCombiner.addText()。

        Args:
            text: 文本内容。
            x, y: 绘制坐标（基线位置）。

        Returns:
            self，支持链式调用。
        """
        if not text:
            return self
        self._draw.text(
            (x, y),
            text,
            fill=self._current_color,
            font=self.current_font,
        )
        return self

    def add_centered_text(self, text: str, y: int, x_offset: int = 0) -> ImageCombiner:
        """添加水平居中的单行文本。

        对应 Java ImageCombiner.addCenteredText()。

        Args:
            text: 文本内容。
            y: Y 坐标。
            x_offset: X 轴偏移量。

        Returns:
            self，支持链式调用。
        """
        if not text:
            return self
        cx = calc_center_x(
            self._draw, text, self._width,
            font=self.current_font, x_offset=x_offset,
        )
        return self.add_text(text, cx, y)

    def add_centered_xy_text(
        self,
        text: str,
        x_offset: int = 0,
        y_offset: int = 0,
    ) -> ImageCombiner:
        """添加完全居中（X、Y 轴）的单行文本。

        对应 Java ImageCombiner.addCenteredXYText()。

        Args:
            text: 文本内容。
            x_offset: X 轴偏移。
            y_offset: Y 轴偏移。

        Returns:
            self，支持链式调用。
        """
        if not text:
            return self
        cx, cy = calc_center_xy(
            self._draw, text, self._width, self._height,
            font=self.current_font,
            x_offset=x_offset, y_offset=y_offset,
        )
        return self.add_text(text, cx, cy)

    def add_multiline_text(
        self,
        text: str,
        x: int,
        start_y: int,
        line_height: int | None = None,
        spacing: int = 4,
    ) -> ImageCombiner:
        """绘制多行文本（按 \\n 手动换行）。

        对应 Java ImageCombiner.addMultilineText()。

        Args:
            text: 文本内容（支持 \\n 换行）。
            x: X 坐标。
            start_y: 起始 Y 坐标。
            line_height: 行高（None 自动计算）。
            spacing: 行间距。

        Returns:
            self，支持链式调用。
        """
        if not text:
            return self

        lines = text.split("\n")
        if line_height is None:
            line_height = calc_line_height(self.current_font)

        current_y = start_y
        for line in lines:
            self.add_text(line, x, current_y)
            current_y += line_height + spacing

        return self

    def add_multiline_centered_text(
        self,
        text: str,
        start_y: int,
        line_height: int | None = None,
        spacing: int = 4,
    ) -> ImageCombiner:
        """绘制多行居中文本。

        对应 Java ImageCombiner.addMultilineCenteredText()。

        Args:
            text: 文本内容。
            start_y: 起始 Y 坐标。
            line_height: 行高。
            spacing: 行间距。

        Returns:
            self，支持链式调用。
        """
        if not text:
            return self

        lines = text.split("\n")
        if line_height is None:
            line_height = calc_line_height(self.current_font)

        current_y = start_y
        for line in lines:
            cx = calc_center_x(
                self._draw, line, self._width,
                font=self.current_font,
            )
            self.add_text(line, cx, current_y)
            current_y += line_height + spacing

        return self

    def add_multiline_wrapped_text(
        self,
        text: str,
        x: int,
        start_y: int,
        max_width: int,
        line_height: int | None = None,
        spacing: int = 4,
    ) -> ImageCombiner:
        """绘制多行文本（自动换行）。

        对应 Java ImageCombiner.addMultilineTextWithWrap()。

        Args:
            text: 文本内容。
            x: X 坐标。
            start_y: 起始 Y 坐标。
            max_width: 最大宽度。
            line_height: 行高。
            spacing: 行间距。

        Returns:
            self，支持链式调用。
        """
        if not text:
            return self

        lines = wrap_text(self._draw, text, max_width, self.current_font)
        if line_height is None:
            line_height = calc_line_height(self.current_font)

        current_y = start_y
        for line in lines:
            self.add_text(line, x, current_y)
            current_y += line_height + spacing

        return self

    def add_text_with_background(
        self,
        text: str,
        x: int,
        y: int,
        bg_color: tuple[int, int, int] | None = None,
        border_color: tuple[int, int, int] | None = None,
        corner_radius: int = 4,
        padding: int = 4,
    ) -> ImageCombiner:
        """绘制带背景框的单行文本。

        对应 Java ImageCombiner.addTextWithBackground()。

        Args:
            text: 文本。
            x, y: 坐标。
            bg_color: 背景颜色。
            border_color: 边框颜色。
            corner_radius: 圆角半径。
            padding: 内边距。

        Returns:
            self，支持链式调用。
        """
        if not text:
            return self
        draw_text_with_background(
            self._draw,
            text, x, y,
            font=self.current_font,
            text_color=self._current_color,
            bg_color=bg_color,
            border_color=border_color,
            corner_radius=corner_radius,
            padding=padding,
        )
        return self

    def add_text_with_shadow(
        self,
        text: str,
        x: int,
        y: int,
        shadow_color: tuple[int, int, int],
        shadow_offset_x: int = 1,
        shadow_offset_y: int = 1,
    ) -> ImageCombiner:
        """绘制带阴影的文本。

        对应 Java ImageCombiner.addTextWithShadow()。

        Args:
            text: 文本。
            x, y: 坐标。
            shadow_color: 阴影颜色。
            shadow_offset_x: 阴影 X 偏移。
            shadow_offset_y: 阴影 Y 偏移。

        Returns:
            self，支持链式调用。
        """
        if not text:
            return self
        draw_text_with_shadow(
            self._draw,
            text, x, y,
            font=self.current_font,
            text_color=self._current_color,
            shadow_color=shadow_color,
            shadow_offset_x=shadow_offset_x,
            shadow_offset_y=shadow_offset_y,
        )
        return self

    # ========================================================================
    # 高级文本绘制
    # ========================================================================

    def draw_advanced_text(
        self,
        text: str,
        max_width: int,
        align: TextAlign = TextAlign.LEFT,
        is_vertical_center: bool = False,
        bg_color: tuple[int, int, int] | None = None,
        gradient_start: tuple[int, int, int] | None = None,
        gradient_end: tuple[int, int, int] | None = None,
        gradient_vertical: bool = False,
        border_color: tuple[int, int, int] | None = None,
        corner_radius: int = 8,
        padding: int = 10,
        shadow_color: tuple[int, int, int] | None = None,
        shadow_offset_x: int = 1,
        shadow_offset_y: int = 1,
        line_spacing: int = 4,
    ) -> ImageCombiner:
        """高级文本绘制：自动换行 + 背景/渐变 + 边框 + 圆角 + 阴影 + 对齐。

        对应 Java ImageCombiner.drawAdvancedText()。

        Returns:
            self，支持链式调用。
        """
        draw_advanced_text(
            self._draw,
            text,
            max_width=max_width,
            canvas_width=self._width,
            canvas_height=self._height,
            font=self.current_font,
            text_color=self._current_color,
            align=align,
            is_vertical_center=is_vertical_center,
            bg_color=bg_color,
            gradient_start=gradient_start,
            gradient_end=gradient_end,
            is_vertical_gradient=gradient_vertical,
            border_color=border_color,
            corner_radius=corner_radius,
            padding=padding,
            shadow_color=shadow_color,
            shadow_offset_x=shadow_offset_x,
            shadow_offset_y=shadow_offset_y,
            line_spacing=line_spacing,
        )
        return self

    # ========================================================================
    # 预设样式
    # ========================================================================

    def draw_title(self, text: str) -> ImageCombiner:
        """预设标题样式：居中 + 渐变背景 + 白色边框 + 阴影。

        对应 Java ImageCombiner.drawTitle()。

        Args:
            text: 标题文本。

        Returns:
            self，支持链式调用。
        """
        return self.draw_advanced_text(
            text=text,
            max_width=self._width - 40,
            align=TextAlign.CENTER,
            is_vertical_center=True,
            gradient_start=(70, 130, 180),
            gradient_end=(100, 149, 237),
            gradient_vertical=False,
            border_color=(255, 255, 255),
            corner_radius=15,
            padding=15,
            shadow_color=(100, 100, 100),  # 灰色阴影
            shadow_offset_x=1,
            shadow_offset_y=1,
        )

    def draw_content_box(self, text: str) -> ImageCombiner:
        """预设正文样式：左对齐 + 暗色背景 + 细边框。

        Args:
            text: 正文文本。

        Returns:
            self，支持链式调用。
        """
        return self.draw_advanced_text(
            text=text,
            max_width=self._width - 40,
            align=TextAlign.LEFT,
            is_vertical_center=False,
            bg_color=ThemeColor.BG_CARD,
            border_color=ThemeColor.DIVIDER,
            corner_radius=8,
            padding=10,
        )

    def draw_double_border(
        self,
        border_padding: int = 20,
        border_color_outer: tuple[int, int, int] = (0xB1, 0xB1, 0xB1),
        border_color_inner: tuple[int, int, int] = (0x33, 0x33, 0x33),
        stroke: int = 4,
    ) -> ImageCombiner:
        """绘制双层边框。

        对应 Java ImageCombiner.drawTooRoundRect()。

        Args:
            border_padding: 边框与边缘的距离。
            border_color_outer: 外层边框颜色。
            border_color_inner: 内层边框颜色。
            stroke: 边框宽度。

        Returns:
            self，支持链式调用。
        """
        inner_width = self._width - border_padding * 2
        inner_height = self._height - border_padding * 2
        offset = 8

        # 外层 — 向外扩展 offset，形成外圈边框
        self._draw.rounded_rectangle(
            [
                (border_padding - offset, border_padding - offset),
                (border_padding + inner_width + offset, border_padding + inner_height + offset),
            ],
            radius=20,
            outline=border_color_outer,
            width=stroke,
        )

        # 内层 — 从 border_padding 开始（不是 -offset），
        # 确保左侧和上侧也可见双层效果（内外层不再共享同一左/上边缘）
        self._draw.rounded_rectangle(
            [
                (border_padding, border_padding),
                (border_padding + inner_width, border_padding + inner_height),
            ],
            radius=20,
            outline=border_color_inner,
            width=stroke,
        )

        return self

    def draw_default_double_border(self) -> ImageCombiner:
        """绘制标准双层边框 — 消除 12+ 个 card_*.py 中的重复样板。

        使用大多数卡片统一的参数: padding=16, 外层 TABLE_BORDER, 内层 DIVIDER, stroke=3。
        """
        return self.draw_double_border(
            border_padding=16,
            border_color_outer=ThemeColor.TABLE_BORDER,
            border_color_inner=ThemeColor.DIVIDER,
            stroke=3,
        )

    def draw_content_divider(
        self, y: int, content_x: int | None = None, content_w: int | None = None
    ) -> ImageCombiner:
        """在内容宽度内绘制水平分割线 — 消除 9+ 个 card_*.py 中的重复样板。

        Args:
            y: 分割线的 Y 坐标。
            content_x: 起始 X 坐标（默认使用 LayoutConstants.CONTENT_X）。
            content_w: 内容宽度（默认使用 LayoutConstants.CONTENT_W_DEFAULT）。
        """
        cx = content_x if content_x is not None else LayoutConstants.CONTENT_X
        cw = content_w if content_w is not None else LayoutConstants.CONTENT_W_DEFAULT
        self.set_color(ThemeColor.DIVIDER)
        return self.draw_line(cx, y, cx + cw, y, width=1)

    def draw_card_footer(
        self,
        canvas_h: int,
        footer_offset: int = 55,
        footer_font_size: int = 20,
    ) -> ImageCombiner:
        """绘制卡片底部居中署名 — 消除 20 个 card_*.py 中的重复样板。

        Args:
            canvas_h: 画布总高度。
            footer_offset: 页脚文字距画布底部的偏移量。
            footer_font_size: 页脚字体大小（默认 20）。
        """
        footer_font = FontManager.get_text_font(footer_font_size)
        self.set_color(ThemeColor.TEXT_MUTED).set_font(footer_font)
        return self.add_centered_text(DrawConstant.FOOTER_TEXT, canvas_h - footer_offset)

    # ========================================================================
    # 工具方法
    # ========================================================================

    def get_string_width(self, text: str) -> int:
        """获取字符串在当前字体下的绘制宽度。

        对应 Java ImageCombiner.getStringWidth()。

        Args:
            text: 文本内容。

        Returns:
            宽度（像素）。
        """
        return get_text_width(self._draw, text, self.current_font)

    def get_canvas_width(self) -> int:
        """获取画布宽度。"""
        return self._width

    def get_canvas_height(self) -> int:
        """获取画布高度。"""
        return self._height

    def get_center_x(self, text: str, x_offset: int = 0) -> int:
        """计算文本水平居中 X 坐标。

        Args:
            text: 文本内容。
            x_offset: X 偏移量。

        Returns:
            居中 X 坐标。
        """
        return calc_center_x(
            self._draw, text, self._width,
            font=self.current_font, x_offset=x_offset,
        )

    # ========================================================================
    # 输出
    # ========================================================================

    def combine(self) -> bytes:
        """合并所有绘制操作，生成最终图片字节数据。

        对应 Java ImageCombiner.combine()。

        Returns:
            PNG/JPEG 格式的图片字节数据。
        """
        buf = io.BytesIO()

        # 根据输出格式决定是否转换为 RGB（JPEG 不支持 RGBA）
        if self._format == OutputFormat.JPG:
            output_img = self._image.convert("RGB")
        else:
            output_img = self._image

        output_img.save(buf, format=self._format.value)
        return buf.getvalue()

    def to_image(self) -> Image.Image:
        """返回当前 PIL Image 对象（不进行 combine）。

        Returns:
            PIL Image 对象。
        """
        return self._image
