"""Image composer / 图片合成工具（替代 Java ImageCombiner）

用于多图叠加合成的场景，如紫卡分析图等需要多图叠加的场景。
"""
from __future__ import annotations

from PIL import Image


class ImageComposer:
    """图片合成工具（替代 Java ImageCombiner）。

    提供多图叠加、裁剪、缩放等常用合成操作。
    """

    @staticmethod
    def composite(
        background: Image.Image,
        overlay: Image.Image,
        position: tuple[int, int],
    ) -> Image.Image:
        """将 overlay 图像合成到 background 的指定位置。

        Args:
            background: 背景图像。
            overlay: 叠加图像（支持 RGBA 透明度）。
            position: (x, y) 位置坐标。

        Returns:
            合成后的新图像。
        """
        result = background.copy()
        if overlay.mode == "RGBA":
            result.paste(overlay, position, overlay)
        else:
            result.paste(overlay, position)
        return result

    @staticmethod
    def composite_center(
        background: Image.Image,
        overlay: Image.Image,
    ) -> Image.Image:
        """将 overlay 居中合成到 background 上。

        Args:
            background: 背景图像。
            overlay: 叠加图像。

        Returns:
            合成后的新图像。
        """
        x = (background.width - overlay.width) // 2
        y = (background.height - overlay.height) // 2
        return ImageComposer.composite(background, overlay, (x, y))

    @staticmethod
    def resize_to_fit(
        image: Image.Image,
        max_width: int,
        max_height: int,
        keep_aspect: bool = True,
    ) -> Image.Image:
        """缩放图像以适应最大尺寸。

        Args:
            image: 原始图像。
            max_width: 最大宽度。
            max_height: 最大高度。
            keep_aspect: 是否保持宽高比。

        Returns:
            缩放后的图像。
        """
        if not keep_aspect:
            return image.resize((max_width, max_height), Image.Resampling.LANCZOS)

        ratio = min(max_width / image.width, max_height / image.height)
        new_size = (int(image.width * ratio), int(image.height * ratio))
        return image.resize(new_size, Image.Resampling.LANCZOS)

    @staticmethod
    def create_collage(
        images: list[Image.Image],
        cols: int = 2,
        spacing: int = 10,
        bg_color: tuple[int, int, int] = (26, 26, 46),
    ) -> Image.Image:
        """将多张图片拼贴为网格布局。

        Args:
            images: 图片列表。
            cols: 列数。
            spacing: 图片间距。
            bg_color: 背景颜色。

        Returns:
            拼贴后的图像。
        """
        if not images:
            raise ValueError("图片列表不能为空")

        # 统一所有图片尺寸为第一张图片的尺寸
        ref_w, ref_h = images[0].size
        rows = (len(images) + cols - 1) // cols

        canvas_w = cols * ref_w + (cols - 1) * spacing
        canvas_h = rows * ref_h + (rows - 1) * spacing
        canvas = Image.new("RGB", (canvas_w, canvas_h), bg_color)

        for idx, img in enumerate(images):
            row = idx // cols
            col = idx % cols
            x = col * (ref_w + spacing)
            y = row * (ref_h + spacing)
            canvas.paste(img.resize((ref_w, ref_h), Image.Resampling.LANCZOS), (x, y))

        return canvas
