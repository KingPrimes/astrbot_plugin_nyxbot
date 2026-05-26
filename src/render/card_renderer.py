"""Card renderer — Pillow 信息卡片渲染器（主引擎）

基于 Pillow + ImageCombiner 绘制 Warframe 信息卡片。
使用 FontManager 管理字体，支持通过 warframe_font_icon.ttf 绘制派系图标。

设计原则：
- 每张卡片使用 ImageCombiner 建造者模式绘制
- 使用预定义 ThemeColor 配色模板，确保视觉一致性
- FactionEnum.icon 通过 warframe_font_icon.ttf 渲染
- MissionTypeEnum.color 动态着色
- 各卡片的具体渲染逻辑已拆分至独立的 card_*.py 文件中
"""
from __future__ import annotations

import asyncio
import io
from collections.abc import Callable
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    from astrbot.api.message_components import BaseMessageComponent

from ..wenum.faction import FactionEnum
from ..wenum.mission_type import MissionTypeEnum
from .draw_constant import ThemeColor, hex_to_rgb
from .font_manager import FontManager


class CardRenderer:
    """Pillow 信息卡片渲染器 — 使用建造者模式 ImageCombiner。

    所有 Warframe 信息卡片（警报、突击、裂隙等）均由本渲染器统一绘制。
    具体绘制逻辑委托给各 card_*.py 中的独立函数。
    """

    # Warframe 暗色主题色板（向后兼容）
    COLORS = {
        "bg_dark": ThemeColor.BG_DARK,
        "bg_card": ThemeColor.BG_CARD,
        "bg_card_alt": ThemeColor.BG_CARD_ALT,
        "accent": ThemeColor.ACCENT,
        "accent_blue": ThemeColor.ACCENT_BLUE,
        "accent_green": ThemeColor.ACCENT_GREEN,
        "accent_gold": ThemeColor.ACCENT_GOLD,
        "text_primary": ThemeColor.TEXT_PRIMARY,
        "text_secondary": ThemeColor.TEXT_SECONDARY,
        "text_muted": ThemeColor.TEXT_MUTED,
        "reward_bg": ThemeColor.REWARD_BG,
        "divider": ThemeColor.DIVIDER,
        "success": ThemeColor.SUCCESS,
        "warning": ThemeColor.WARNING,
        "danger": ThemeColor.DANGER,
        "info": ThemeColor.INFO,
    }

    # 字体大小预设
    FONT_SIZES = {
        "title": 26,
        "subtitle": 20,
        "body": 16,
        "small": 13,
        "tiny": 11,
        "icon_faction": 36,   # 派系图标
        "icon_large": 48,      # 大图标
    }

    # 预构建 O(1) 查找字典 — 消除每次调用时的全枚举遍历
    _FACTION_LOOKUP: dict[str, tuple[str, tuple[int, int, int]]] = {}
    _MISSION_TYPE_LOOKUP: dict[str, tuple[int, int, int]] = {}

    @classmethod
    def _build_lookup_caches(cls) -> None:
        """延迟构建枚举查找缓存（模块导入后自动调用一次）。"""
        if cls._FACTION_LOOKUP:
            return
        for fe in FactionEnum:
            rgb = hex_to_rgb(fe.color)
            cls._FACTION_LOOKUP[fe.display_name.lower()] = (fe.icon, rgb)
            cls._FACTION_LOOKUP[fe.name.lower()] = (fe.icon, rgb)
            cls._FACTION_LOOKUP[fe.name.removeprefix("FC_").lower()] = (fe.icon, rgb)
        for mt in MissionTypeEnum:
            rgb = hex_to_rgb(mt.color)
            cls._MISSION_TYPE_LOOKUP[mt.display_name] = rgb
            cls._MISSION_TYPE_LOOKUP[mt.name.lower()] = rgb
            cls._MISSION_TYPE_LOOKUP[mt.name.removeprefix("MT_").lower().replace("_", " ")] = rgb

    def __init__(self, font_path: str | None = None):
        """初始化渲染器，加载字体。

        Args:
            font_path: 文本字体路径（None 使用 FontManager 自动查找）。
        """
        self._font_path = font_path
        self._load_fonts()

    def _load_fonts(self):
        """加载字体 — 使用 FontManager 管理。"""
        # 文本字体（各级大小）
        self.font_title = FontManager.get_text_font(self.FONT_SIZES["title"])
        self.font_subtitle = FontManager.get_text_font(self.FONT_SIZES["subtitle"])
        self.font_body = FontManager.get_text_font(self.FONT_SIZES["body"])
        self.font_small = FontManager.get_text_font(self.FONT_SIZES["small"])
        self.font_tiny = FontManager.get_text_font(self.FONT_SIZES["tiny"])

        # Warframe 图标字体（用于派系图标等）
        try:
            self.font_wf_icon = FontManager.get_wf_icon_font(self.FONT_SIZES["icon_faction"])
            self.font_wf_icon_large = FontManager.get_wf_icon_font(self.FONT_SIZES["icon_large"])
        except FileNotFoundError:
            self.font_wf_icon = None
            self.font_wf_icon_large = None

    # ========================================================================
    # 派系图标辅助方法
    # ========================================================================

    @staticmethod
    def resolve_faction_icon_and_color(faction: FactionEnum | str | None) -> tuple[str, tuple[int, int, int]]:
        """根据派系名称解析图标字符和颜色 — O(1) 预构建字典查找。

        支持直接传入 FactionEnum 枚举值或字符串（英文/中文）。
        """
        if faction is None:
            return ("", ThemeColor.TEXT_MUTED)

        if isinstance(faction, FactionEnum):
            return (faction.icon, hex_to_rgb(faction.color))

        CardRenderer._build_lookup_caches()
        key = faction.lower().strip()
        return CardRenderer._FACTION_LOOKUP.get(key, ("", ThemeColor.TEXT_MUTED))

    @staticmethod
    def resolve_mission_type_color(mission_type: MissionTypeEnum | str | None) -> tuple[int, int, int]:
        """根据任务类型获取颜色 — O(1) 预构建字典查找。

        支持直接传入 MissionTypeEnum 枚举值或字符串（英文/中文）。
        """
        if mission_type is None:
            return ThemeColor.TEXT_SECONDARY

        if isinstance(mission_type, MissionTypeEnum):
            return hex_to_rgb(mission_type.color)

        CardRenderer._build_lookup_caches()
        key = mission_type.strip()
        # 先尝试精确匹配 display_name，再尝试 lower 匹配
        result = CardRenderer._MISSION_TYPE_LOOKUP.get(key)
        if result is not None:
            return result
        return CardRenderer._MISSION_TYPE_LOOKUP.get(key.lower(), ThemeColor.TEXT_SECONDARY)

    # ========================================================================
    # 通用工具
    # ========================================================================

    @staticmethod
    def render_to_bytes(img: Image.Image, fmt: str = "PNG") -> bytes:
        """将 PIL Image 转为 bytes 供 AstrBot 发送。"""
        buf = io.BytesIO()
        img.save(buf, format=fmt)
        return buf.getvalue()

    @staticmethod
    async def render_card_to_chain_result(
        render_func: Callable[..., Image.Image], *args: object, **kwargs: object
    ) -> list[BaseMessageComponent]:
        """消除 17 个命令文件中重复的 renderer + run_in_executor 样板。

        用法::

            result = await CardRenderer.render_card_to_chain_result(
                render_alert_card, alerts
            )
            yield event.chain_result(result)
        """
        renderer = CardRenderer()
        loop = asyncio.get_running_loop()
        img_bytes = await loop.run_in_executor(
            None,
            lambda: CardRenderer.render_to_bytes(render_func(renderer, *args, **kwargs)),
        )
        # 延迟导入避免循环依赖
        import astrbot.api.message_components as Comp

        return [Comp.Image.fromBytes(img_bytes)]

    @staticmethod
    def create_text_image(text: str, width: int = 600, height: int = 200) -> Image.Image:
        """创建纯文字图片（用于错误提示或简单信息）。"""
        img = Image.new("RGB", (width, height), ThemeColor.BG_DARK)
        draw = ImageDraw.Draw(img)
        try:
            font = FontManager.get_text_font(20)
        except Exception:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = int(bbox[2] - bbox[0])
        text_h = int(bbox[3] - bbox[1])
        x = (width - text_w) // 2
        y = (height - text_h) // 2
        draw.text((x, y), text, fill=ThemeColor.TEXT_PRIMARY, font=font)
        return img
