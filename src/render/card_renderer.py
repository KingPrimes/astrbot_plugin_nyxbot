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

import io
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from ..wenum.faction import FactionEnum
from ..wenum.mission_type import MissionTypeEnum
from .draw_constant import ThemeColor, hex_to_rgb
from .font_manager import FontManager

if TYPE_CHECKING:
    from ..model.world_state import (
        Alert,
        AllCycles,
        DailyDeals,
        DuvalierCycle,
        Invasion,
        SeasonInfo,
        Sortie,
        SteelPathOffering,
        VoidTrader,
    )


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
        """根据派系名称解析图标字符和颜色。

        支持直接传入 FactionEnum 枚举值或字符串（英文/中文）。
        在 FactionEnum 中按 display_name 或成员名匹配。

        Args:
            faction: FactionEnum 枚举值、派系名称（英文或中文）或 None。

        Returns:
            (icon_unicode_string, rgb_color) 元组。未匹配时返回 ("", (120,120,120))。
        """
        if faction is None:
            return ("", ThemeColor.TEXT_MUTED)

        # 如果已经是 FactionEnum 实例，直接取图标和颜色
        if isinstance(faction, FactionEnum):
            rgb = hex_to_rgb(faction.color)
            return (faction.icon, rgb)

        faction_name_lower = faction.lower().strip()

        for fe in FactionEnum:
            if fe.display_name.lower() == faction_name_lower:
                rgb = hex_to_rgb(fe.color)
                return (fe.icon, rgb)
            # 匹配完整枚举名（如 "FC_CORPUS"）
            if fe.name.lower() == faction_name_lower:
                rgb = hex_to_rgb(fe.color)
                return (fe.icon, rgb)
            # 也尝试匹配去掉 FC_ 前缀的成员名
            enum_name = fe.name.removeprefix("FC_").lower()
            if enum_name == faction_name_lower:
                rgb = hex_to_rgb(fe.color)
                return (fe.icon, rgb)

        return ("", ThemeColor.TEXT_MUTED)

    @staticmethod
    def resolve_mission_type_color(mission_type: MissionTypeEnum | str | None) -> tuple[int, int, int]:
        """根据任务类型获取颜色。

        支持直接传入 MissionTypeEnum 枚举值或字符串（英文/中文）。

        Args:
            mission_type: MissionTypeEnum 枚举值、任务类型名称或 None。

        Returns:
            RGB 颜色元组。
        """
        if mission_type is None:
            return ThemeColor.TEXT_SECONDARY

        # 如果已经是 MissionTypeEnum 实例，直接取颜色
        if isinstance(mission_type, MissionTypeEnum):
            return hex_to_rgb(mission_type.color)

        mt_lower = mission_type.lower().strip()

        for mt in MissionTypeEnum:
            if mt.display_name == mission_type:
                return hex_to_rgb(mt.color)
            # 匹配完整枚举名（如 "MT_MOBILE_DEFENSE"）
            if mt.name.lower() == mt_lower:
                return hex_to_rgb(mt.color)
            # 也尝试匹配去掉 MT_ 前缀的成员名
            enum_name = mt.name.removeprefix("MT_").lower().replace("_", " ")
            if enum_name == mt_lower:
                return hex_to_rgb(mt.color)

        return ThemeColor.TEXT_SECONDARY

    # ========================================================================
    # 卡片绘制方法 — 委托给独立的 card_*.py 模块
    # ========================================================================

    def create_alert_card(self, alerts: list[Alert]) -> Image.Image:
        """绘制警报信息卡片。"""
        from .card_alert import render_alert_card
        return render_alert_card(self, alerts)

    def create_sortie_card(self, sortie: Sortie) -> Image.Image:
        """绘制突击信息卡片。"""
        from .card_sortie import render_sortie_card
        return render_sortie_card(self, sortie)

    def create_fissure_card(self, fissures: list[dict]) -> Image.Image:
        """绘制裂隙信息卡片。"""
        from .card_fissures import render_fissure_card
        return render_fissure_card(self, fissures)

    def create_invasion_card(self, invasions: list[Invasion]) -> Image.Image:
        """绘制入侵信息卡片。"""
        from .card_invasions import render_invasion_card
        return render_invasion_card(self, invasions)

    def create_void_trader_card(self, trader: VoidTrader) -> Image.Image:
        """绘制虚空商人信息卡片。"""
        from .card_void_trader import render_void_trader_card
        return render_void_trader_card(self, trader)

    def create_arbitration_card(self, arbitration: dict) -> Image.Image:
        """绘制仲裁信息卡片。"""
        from .card_arbitration import render_arbitration_card
        return render_arbitration_card(self, arbitration)

    def create_cycle_card(self, cycles: AllCycles, title: str = "平原周期") -> Image.Image:
        """绘制周期信息卡片。"""
        from .card_cycle import render_cycle_card
        return render_cycle_card(self, cycles, title)

    def create_daily_deals_card(self, deals: list[DailyDeals]) -> Image.Image:
        """绘制每日特惠卡片。"""
        from .card_daily_deals import render_daily_deals_card
        return render_daily_deals_card(self, deals)

    def create_steel_path_card(self, steel_path: SteelPathOffering) -> Image.Image:
        """绘制钢铁之路卡片。"""
        from .card_steel_path import render_steel_path_card
        return render_steel_path_card(self, steel_path)

    def create_nightwave_card(self, nightwave: SeasonInfo) -> Image.Image:
        """绘制午夜电波卡片。"""
        from .card_nightwave import render_nightwave_card
        return render_nightwave_card(self, nightwave)

    def create_relic_card(self, relics: list[dict]) -> Image.Image:
        """绘制遗物信息卡片。"""
        from .card_relics import render_relic_card
        return render_relic_card(self, relics)

    def create_duviri_card(self, duviri: DuvalierCycle) -> Image.Image:
        """绘制双衍王境信息卡片。"""
        from .card_duviri import render_duviri_card
        return render_duviri_card(self, duviri)

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
