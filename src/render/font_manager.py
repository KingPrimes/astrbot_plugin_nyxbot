"""Font manager / 字体管理模块

提供常用字体定义和字体加载功能，替代原 CardRenderer._find_font() 和 _load_fonts()。
- 优先使用项目内置字体（src/render/fonts/）
- 支持 warframe_font_icon.ttf 用于绘制 FactionEnum 等枚举中的 Unicode 图标
- 字体缓存避免重复创建字体对象
"""
from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from PIL import ImageFont

try:
    from astrbot.api import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class FontManager:
    """字体管理器 — 提供常用字体定义和字体加载功能。

    对应 Java Fonts.java + DrawConstants 中的字体部分。

    用法::

        text_font = FontManager.get_text_font(32)
        icon_font = FontManager.get_wf_icon_font(48)
    """

    # 默认字体大小
    DEFAULT_FONT_SIZE: ClassVar[int] = 24
    SMALL_FONT_SIZE: ClassVar[int] = 15
    LARGE_FONT_SIZE: ClassVar[int] = 32

    # 字体文件名称 (相对于 fonts/ 子目录)
    _TEXT_FONT_FILENAME: ClassVar[str] = "SourceHanSerifCN-Bold.ttf"
    _ICON_FONT_FILENAME: ClassVar[str] = "warframe_font_icon.ttf"

    # 字体缓存: key = "path:size" → ImageFont.FreeTypeFont
    _font_cache: ClassVar[dict[str, ImageFont.FreeTypeFont]] = {}

    # 系统回退字体候选路径
    _SYSTEM_FALLBACK_CANDIDATES: ClassVar[list[str]] = [
        "C:/Windows/Fonts/msyh.ttc",                                 # Windows 微软雅黑
        "C:/Windows/Fonts/simhei.ttf",                               # Windows 黑体
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",            # Linux 文泉驿
        "/System/Library/Fonts/PingFang.ttc",                        # macOS 苹方
    ]

    # 一次性解析的字体目录绝对路径
    _fonts_dir: ClassVar[Path | None] = None

    @classmethod
    def _get_fonts_dir(cls) -> Path:
        """获取项目字体目录的绝对路径。"""
        if cls._fonts_dir is None:
            cls._fonts_dir = (Path(__file__).parent / "fonts").resolve()
        return cls._fonts_dir

    @classmethod
    def _find_font_file(cls, filename: str) -> str | None:
        """在项目字体目录中查找字体文件。

        Args:
            filename: 字体文件名（如 "SourceHanSerifCN-Bold.ttf"）

        Returns:
            字体文件绝对路径，未找到返回 None。
        """
        candidate = cls._get_fonts_dir() / filename
        if candidate.exists():
            return str(candidate)
        return None

    @classmethod
    def _find_system_fallback(cls) -> str | None:
        """查找系统回退字体。"""
        for path in cls._SYSTEM_FALLBACK_CANDIDATES:
            if Path(path).exists():
                return path
        return None

    @classmethod
    def get_font(cls, font_path: str, size: int) -> ImageFont.FreeTypeFont:
        """加载指定路径的字体并缓存。

        对应 Java Fonts.createFont()。
        缓存 key = "path:size"。

        Args:
            font_path: 字体文件路径。
            size: 字体大小。

        Returns:
            加载的字体对象。若加载失败则抛出异常。
        """
        cache_key = f"{font_path}:{size}"

        if cache_key in cls._font_cache:
            return cls._font_cache[cache_key]

        if not Path(font_path).exists():
            raise FileNotFoundError(f"字体文件不存在: {font_path}")

        try:
            font = ImageFont.truetype(font_path, size)
            cls._font_cache[cache_key] = font
            logger.debug(f"加载字体: {font_path} (size={size})")
            return font
        except Exception:
            logger.error(f"创建字体失败: {font_path} (size={size})")
            raise

    @classmethod
    def get_text_font(cls, size: int | None = None) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """获取项目文本字体（SourceHanSerifCN-Bold）。

        优先使用项目内置字体，回退到系统字体。

        Args:
            size: 字体大小，默认使用 LARGE_FONT_SIZE (32)。

        Returns:
            文本字体对象。
        """
        if size is None:
            size = cls.LARGE_FONT_SIZE

        path = cls._find_font_file(cls._TEXT_FONT_FILENAME)
        if path is not None:
            return cls.get_font(path, size)

        # 回退到系统字体
        fallback = cls._find_system_fallback()
        if fallback is not None:
            logger.warning(f"项目文本字体未找到，使用系统回退: {fallback}")
            return cls.get_font(fallback, size)

        # 最终兜底：Pillow 默认字体
        logger.error("未找到任何可用字体！使用 Pillow 默认字体")
        return ImageFont.load_default()

    @classmethod
    def get_wf_icon_font(cls, size: int | None = None) -> ImageFont.FreeTypeFont:
        """获取 Warframe 图标字体（warframe_font_icon.ttf）。

        用于绘制 FactionEnum 等枚举中的 Unicode 图标字符（如 \\ue400-\\ue413）。

        对应 Java Fonts.FONT_WARFRAME_ICON。

        Args:
            size: 字体大小，默认使用 LARGE_FONT_SIZE (32)。

        Returns:
            Warframe 图标字体对象。

        Raises:
            FileNotFoundError: 若图标字体文件未找到（此字体为必须项，不回退）。
        """
        if size is None:
            size = cls.LARGE_FONT_SIZE

        path = cls._find_font_file(cls._ICON_FONT_FILENAME)
        if path is None:
            raise FileNotFoundError(
                f"Warframe 图标字体未找到: {cls._ICON_FONT_FILENAME}。"
                f"请确保该文件存在于 {cls._get_fonts_dir()}"
            )
        return cls.get_font(path, size)

    @classmethod
    def get_cached_font_count(cls) -> int:
        """获取缓存的字体数量（用于调试）。"""
        return len(cls._font_cache)

    @classmethod
    def clear_font_cache(cls) -> None:
        """清除字体缓存。"""
        cls._font_cache.clear()
        logger.debug("字体缓存已清除")
