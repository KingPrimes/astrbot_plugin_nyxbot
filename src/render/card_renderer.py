"""Card renderer — Pillow 信息卡片渲染器（主引擎）

基于 Pillow + ImageCombiner 绘制 Warframe 信息卡片。
使用 FontManager 管理字体，支持通过 warframe_font_icon.ttf 绘制派系图标。

设计原则：
- 每张卡片使用 ImageCombiner 建造者模式绘制
- 使用预定义 ThemeColor 配色模板，确保视觉一致性
- FactionEnum.icon 通过 warframe_font_icon.ttf 渲染
- MissionTypeEnum.color 动态着色
"""
from __future__ import annotations

import io
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from ..wenum.faction import FactionEnum
from ..wenum.mission_type import MissionTypeEnum
from .draw_constant import ThemeColor, hex_to_rgb
from .font_manager import FontManager
from .image_combiner import ImageCombiner

if TYPE_CHECKING:
    from ..model.world_state import (
        Alert,
        DailyDeals,
        Invasion,
        SeasonInfo,
        Sortie,
        SteelPathOffering,
        VoidTrader,
    )


class CardRenderer:
    """Pillow 信息卡片渲染器 — 使用建造者模式 ImageCombiner。

    所有 Warframe 信息卡片（警报、突击、裂隙等）均由本渲染器统一绘制。
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
    def _resolve_faction_icon_and_color(faction: FactionEnum | str | None) -> tuple[str, tuple[int, int, int]]:
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
    def _resolve_mission_type_color(mission_type: MissionTypeEnum | str | None) -> tuple[int, int, int]:
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
    # 卡片绘制方法
    # ========================================================================

    def create_alert_card(self, alerts: list[Alert]) -> Image.Image:
        """绘制警报信息卡片。

        Args:
            alerts: Alert 模型列表。

        Returns:
            PIL Image 对象。
        """

        card_width = 800
        item_height = 110
        padding_top = 60
        card_height = padding_top + len(alerts) * item_height + 20

        cb = ImageCombiner(card_width, max(card_height, 200), ThemeColor.BG_DARK)

        # 标题栏
        cb.set_color(ThemeColor.ACCENT).set_font(self.font_title)
        cb.add_text("⚠ 当前警报", 25, 15)
        cb.set_color(ThemeColor.ACCENT)
        cb.draw_line(25, 48, 775, 48, width=2)

        y_offset = 65
        for i, alert in enumerate(alerts):
            mi = alert.mission_info
            if mi is None:
                continue

            bg_color = ThemeColor.BG_CARD if i % 2 == 0 else ThemeColor.BG_CARD_ALT
            cb.draw_rounded_rect(20, y_offset, 760, 100, radius=8, fill=bg_color)

            # 任务节点名称（已由 Service 翻译）
            node_name = mi.location or "未知节点"
            cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(self.font_body)
            cb.add_text(node_name, 35, y_offset + 10)

            # 派系（带图标）
            faction = mi.faction
            faction_name = faction.display_name if faction else ""
            if faction and self.font_wf_icon:
                icon, faction_color = self._resolve_faction_icon_and_color(faction)
                if icon:
                    cb.set_color(faction_color).set_font(self.font_wf_icon)
                    cb.add_text(icon, 35, y_offset + 33)

            # 任务类型 | 派系
            mission_type = mi.mission_type.display_name if mi.mission_type else "未知任务"
            mt_color = self._resolve_mission_type_color(mi.mission_type)
            x_faction_text = 75 if (faction and self.font_wf_icon) else 35

            # 使用派系图标后，在图标右侧绘制任务类型和派系
            if faction and self.font_wf_icon:
                icon, _ = self._resolve_faction_icon_and_color(faction)
                if icon:
                    cb.set_color(mt_color).set_font(self.font_small)
                    cb.add_text(f"{mission_type}  |  {faction_name}", x_faction_text, y_offset + 38)
                else:
                    cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(self.font_small)
                    cb.add_text(f"{mission_type}  |  {faction_name}", 35, y_offset + 38)
            else:
                cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(self.font_small)
                cb.add_text(f"{mission_type}  |  {faction_name}", 35, y_offset + 38)

            # 等级范围
            min_lv = mi.min_enemy_level or "?"
            max_lv = mi.max_enemy_level or "?"
            cb.set_color(ThemeColor.TEXT_MUTED).set_font(self.font_small)
            cb.add_text(f"Lv.{min_lv} - {max_lv}", 640, y_offset + 10)

            # 倒计时
            eta = alert.time_left
            if eta:
                cb.set_color(ThemeColor.ACCENT_GOLD).set_font(self.font_small)
                cb.add_text(eta, 640, y_offset + 35)

            # 奖励标签（已由 Service 翻译）
            reward = mi.mission_reward
            rewards = [item.name for item in reward.counted_items] if reward else []
            x_reward = 35
            for item_name in rewards[:6]:
                draw_ref = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
                bbox = draw_ref.textbbox((0, 0), item_name, font=self.font_tiny)
                tag_w = bbox[2] - bbox[0] + 16
                tag_h = 22
                cb.draw_rounded_rect(
                    int(x_reward), y_offset + 65,
                    int(tag_w), tag_h,
                    radius=4, fill=ThemeColor.REWARD_BG,
                )
                cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(self.font_tiny)
                cb.add_text(item_name, int(x_reward) + 8, y_offset + 67)
                x_reward += tag_w + 8

            y_offset += item_height

        return cb.to_image()

    def create_sortie_card(self, sortie: Sortie) -> Image.Image:
        """绘制突击信息卡片。

        Args:
            sortie: Sortie 模型。
        """
        card_width = 800
        item_height = 130
        card_height = 60 + len(sortie.variants) * item_height + 20

        cb = ImageCombiner(card_width, max(card_height, 200), ThemeColor.BG_DARK)

        cb.set_color(ThemeColor.ACCENT_GOLD).set_font(self.font_title)
        cb.add_text("⚡ 今日突击", 25, 15)
        cb.draw_line(25, 48, 775, 48, width=2)

        y_offset = 65
        for i, v in enumerate(sortie.variants):
            bg_color = ThemeColor.BG_CARD if i % 2 == 0 else ThemeColor.BG_CARD_ALT
            cb.draw_rounded_rect(20, y_offset, 760, 115, radius=8, fill=bg_color)

            # 阶段标题（使用 modifier_type 名称）
            variant_name = v.modifier_type.name if v.modifier_type else f"阶段 {i + 1}"
            cb.set_color(ThemeColor.ACCENT_BLUE).set_font(self.font_subtitle)
            cb.add_text(variant_name, 35, y_offset + 10)

            # 任务节点（已由 Service 翻译）
            node = v.node or "未知节点"
            mission_type = v.mission_type.name if v.mission_type else "未知任务"
            cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(self.font_body)
            cb.add_text(f"{node}  —  {mission_type}", 35, y_offset + 40)

            # 特殊规则（modifier_type 名称）
            if v.modifier_type:
                cb.set_color(ThemeColor.ACCENT_GOLD).set_font(self.font_small)
                cb.add_text(f"规则: {v.modifier_type.name}", 35, y_offset + 70)

            y_offset += item_height

        return cb.to_image()

    def create_fissure_card(self, fissures: list[dict]) -> Image.Image:
        """绘制裂隙信息卡片。"""
        card_width = 800
        item_height = 80
        card_height = 60 + len(fissures) * item_height + 20

        cb = ImageCombiner(card_width, max(card_height, 200), ThemeColor.BG_DARK)

        cb.set_color(ThemeColor.INFO).set_font(self.font_title)
        cb.add_text("🌀 当前裂隙", 25, 15)
        cb.draw_line(25, 48, 775, 48, width=2)

        y_offset = 65
        tier_order = {4: 0, 3: 1, 2: 2, 1: 3}
        sorted_fissures = sorted(fissures, key=lambda f: tier_order.get(f.get("tier", 0), 5))

        for i, fissure in enumerate(sorted_fissures):
            bg_color = ThemeColor.BG_CARD if i % 2 == 0 else ThemeColor.BG_CARD_ALT
            cb.draw_rounded_rect(20, y_offset, 760, 68, radius=8, fill=bg_color)

            node = fissure.get("node", "未知节点")
            mission_type = fissure.get("mission_type", "未知")
            cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(self.font_body)
            cb.add_text(f"{node}  [{mission_type}]", 35, y_offset + 10)

            tier_name = fissure.get("tier_name", "")
            if tier_name:
                cb.set_color(ThemeColor.ACCENT).set_font(self.font_small)
                cb.add_text(tier_name, 35, y_offset + 38)

            faction = fissure.get("faction", "")
            if faction:
                if self.font_wf_icon:
                    icon, faction_color = self._resolve_faction_icon_and_color(faction)
                    if icon:
                        cb.set_color(faction_color).set_font(self.font_wf_icon)
                        cb.add_text(icon, 640, y_offset + 2)
                cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(self.font_small)
                cb.add_text(faction, 685, y_offset + 10)

            eta = fissure.get("eta", "")
            if eta:
                cb.set_color(ThemeColor.ACCENT_GOLD).set_font(self.font_small)
                cb.add_text(eta, 640, y_offset + 38)

            y_offset += item_height

        return cb.to_image()

    def create_invasion_card(self, invasions: list[Invasion]) -> Image.Image:
        """绘制入侵信息卡片。

        Args:
            invasions: Invasion 模型列表。
        """
        card_width = 800
        item_height = 100
        card_height = 60 + len(invasions) * item_height + 20

        cb = ImageCombiner(card_width, max(card_height, 200), ThemeColor.BG_DARK)

        cb.set_color(ThemeColor.WARNING).set_font(self.font_title)
        cb.add_text("⚔ 当前入侵", 25, 15)
        cb.draw_line(25, 48, 775, 48, width=2)

        y_offset = 65
        for i, inv in enumerate(invasions):
            bg_color = ThemeColor.BG_CARD if i % 2 == 0 else ThemeColor.BG_CARD_ALT
            cb.draw_rounded_rect(20, y_offset, 760, 88, radius=8, fill=bg_color)

            node = inv.node or "未知节点"
            cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(self.font_body)
            cb.add_text(node, 35, y_offset + 10)

            attacker = inv.faction.name if inv.faction else "未知"
            defender = inv.defender_faction.name if inv.defender_faction else "未知"

            # 攻击方图标
            x_atk = 35
            if inv.faction and self.font_wf_icon:
                icon, atk_color = self._resolve_faction_icon_and_color(inv.faction)
                if icon:
                    cb.set_color(atk_color).set_font(self.font_wf_icon)
                    cb.add_text(icon, x_atk, y_offset + 30)
                    x_atk += 45

            cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(self.font_small)
            cb.add_text(f"{attacker}  ⚔  {defender}", x_atk, y_offset + 38)

            # 进度
            completion = int(inv.count or 0)
            progress_color = ThemeColor.SUCCESS if completion > 50 else ThemeColor.WARNING
            cb.set_color(progress_color).set_font(self.font_small)
            cb.add_text(f"进度: {completion}", 640, y_offset + 10)

            # 收集奖励物品名（已由 Service 翻译）
            reward_items: list[str] = []
            for rw in inv.attacker_reward:
                if rw.counted_items:
                    for ci in rw.counted_items:
                        reward_items.append(ci.name)
            if inv.defender_reward and inv.defender_reward.counted_items:
                for ci in inv.defender_reward.counted_items:
                    reward_items.append(ci.name)
            reward_str = ", ".join(reward_items[:4]) if reward_items else ""
            if reward_str:
                cb.set_color(ThemeColor.ACCENT_GOLD).set_font(self.font_tiny)
                cb.add_text(f"奖励: {reward_str}", 640, y_offset + 38)

        return cb.to_image()

    def create_void_trader_card(self, trader: VoidTrader) -> Image.Image:
        """绘制虚空商人信息卡片。

        Args:
            trader: VoidTrader 模型。
        """
        card_width = 800
        item_height = 55
        card_height = 80 + len(trader.manifest) * item_height + 20

        cb = ImageCombiner(card_width, max(card_height, 200), ThemeColor.BG_DARK)

        trader_name = trader.character or "Baro Ki'Teer"
        location = trader.node or "未知中继站"
        cb.set_color(ThemeColor.ACCENT_GOLD).set_font(self.font_title)
        cb.add_text(f"🏪 虚空商人 - {trader_name}", 25, 15)
        cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(self.font_small)
        cb.add_text(f"位置: {location}", 25, 42)

        eta = trader.time_left
        if eta:
            cb.set_color(ThemeColor.ACCENT).set_font(self.font_small)
            cb.add_text(f"剩余: {eta}", 640, 42)

        cb.draw_line(25, 68, 775, 68, width=2)

        y_offset = 82
        for i, m_item in enumerate(trader.manifest):
            bg_color = ThemeColor.BG_CARD if i % 2 == 0 else ThemeColor.BG_CARD_ALT
            cb.draw_rounded_rect(20, y_offset, 760, 45, radius=6, fill=bg_color)

            item_name = m_item.item or "未知物品"
            if "/" in str(item_name):
                item_name = str(item_name).split("/")[-1].replace("_", " ")
            ducats = m_item.prime_price or 0
            credits = m_item.regular_price or 0

            cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(self.font_body)
            cb.add_text(item_name, 35, y_offset + 8)
            cb.set_color(ThemeColor.ACCENT_GOLD).set_font(self.font_small)
            cb.add_text(f"{ducats}  ducats  |  {credits:,}  credits", 500, y_offset + 8)

            y_offset += item_height

        return cb.to_image()

    def create_arbitration_card(self, arbitration: dict) -> Image.Image:
        """绘制仲裁信息卡片。"""
        card_width = 800
        card_height = 200

        cb = ImageCombiner(card_width, card_height, ThemeColor.BG_DARK)

        cb.set_color(ThemeColor.ACCENT_GOLD).set_font(self.font_title)
        cb.add_text("🏅 当前仲裁", 25, 15)
        cb.draw_line(25, 48, 775, 48, width=2)

        node = arbitration.get("node", "未知节点")
        mission_type = arbitration.get("mission_type", "未知任务")
        faction = arbitration.get("faction", "未知派系")

        cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(self.font_body)
        cb.add_text(node, 35, 70)

        # 派系图标
        if faction and self.font_wf_icon:
            icon, faction_color = self._resolve_faction_icon_and_color(faction)
            if icon:
                cb.set_color(faction_color).set_font(self.font_wf_icon)
                cb.add_text(icon, 35, 93)

        mt_color = self._resolve_mission_type_color(mission_type)
        cb.set_color(mt_color).set_font(self.font_small)
        cb.add_text(f"{mission_type}  |  {faction}", 80 if (faction and self.font_wf_icon) else 35, 100)

        eta = arbitration.get("eta", "")
        if eta:
            cb.set_color(ThemeColor.ACCENT).set_font(self.font_small)
            cb.add_text(f"剩余: {eta}", 640, 70)

        return cb.to_image()

    def create_cycle_card(self, cycles: list[dict], title: str = "平原周期") -> Image.Image:
        """绘制周期信息卡片。"""
        card_width = 800
        item_height = 70
        card_height = 60 + len(cycles) * item_height + 20

        cb = ImageCombiner(card_width, max(card_height, 150), ThemeColor.BG_DARK)

        cb.set_color(ThemeColor.ACCENT_GREEN).set_font(self.font_title)
        cb.add_text(f"🌍 {title}", 25, 15)
        cb.draw_line(25, 48, 775, 48, width=2)

        y_offset = 65
        for i, cycle in enumerate(cycles):
            bg_color = ThemeColor.BG_CARD if i % 2 == 0 else ThemeColor.BG_CARD_ALT
            cb.draw_rounded_rect(20, y_offset, 760, 58, radius=8, fill=bg_color)

            name = cycle.get("name", "未知")
            state = cycle.get("state", "未知")
            is_day = cycle.get("is_day", None)
            time_left = cycle.get("time_left", "")

            if is_day is not None:
                state_color = ThemeColor.ACCENT_GOLD if is_day else ThemeColor.INFO
                state_icon = "☀ 白天" if is_day else "🌙 夜晚"
            else:
                state_color = ThemeColor.TEXT_SECONDARY
                state_icon = state

            cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(self.font_body)
            cb.add_text(name, 35, y_offset + 8)
            cb.set_color(state_color).set_font(self.font_small)
            cb.add_text(f"状态: {state_icon}", 35, y_offset + 33)

            if time_left:
                cb.set_color(ThemeColor.ACCENT).set_font(self.font_small)
                cb.add_text(f"剩余: {time_left}", 640, y_offset + 8)

            y_offset += item_height

        return cb.to_image()

    def create_daily_deals_card(self, deals: list[DailyDeals]) -> Image.Image:
        """绘制每日特惠卡片。

        Args:
            deals: DailyDeals 模型列表。
        """
        card_width = 800
        item_height = 65
        card_height = 60 + len(deals) * item_height + 20

        cb = ImageCombiner(card_width, max(card_height, 150), ThemeColor.BG_DARK)

        cb.set_color(ThemeColor.ACCENT_GOLD).set_font(self.font_title)
        cb.add_text("💰 每日特惠", 25, 15)
        cb.draw_line(25, 48, 775, 48, width=2)

        y_offset = 65
        for i, d in enumerate(deals):
            bg_color = ThemeColor.BG_CARD if i % 2 == 0 else ThemeColor.BG_CARD_ALT
            cb.draw_rounded_rect(20, y_offset, 760, 54, radius=8, fill=bg_color)

            item_name = d.item or "未知物品"
            original = d.original_price or 0
            sale = d.sale_price or 0
            discount = d.discount or 0
            total = d.total or 0
            sold = d.sold or 0

            cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(self.font_body)
            cb.add_text(item_name, 35, y_offset + 8)

            if discount > 0:
                cb.set_color(ThemeColor.ACCENT).set_font(self.font_body)
                cb.add_text(f"-{discount:.0f}%", 400, y_offset + 8)

            cb.set_color(ThemeColor.ACCENT_GOLD).set_font(self.font_small)
            cb.add_text(f"原价 {original}p  → 特价 {sale}p", 500, y_offset + 8)

            if total > 0:
                remaining = total - sold
                cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(self.font_tiny)
                cb.add_text(f"剩余 {remaining}/{total}", 500, y_offset + 30)

            y_offset += item_height

        return cb.to_image()

    def create_steel_path_card(self, steel_path: SteelPathOffering) -> Image.Image:
        """绘制钢铁之路卡片。

        Args:
            steel_path: SteelPathOffering 模型。
        """
        card_width = 800
        essences = steel_path.evergreens
        item_height = 55
        card_height = 80 + len(essences) * item_height + 20

        cb = ImageCombiner(card_width, max(card_height, 180), ThemeColor.BG_DARK)

        cb.set_color(ThemeColor.ACCENT).set_font(self.font_title)
        cb.add_text("⚔ 钢铁之路", 25, 15)
        cb.draw_line(25, 48, 775, 48, width=2)

        rotation = steel_path.current_reward.name if steel_path.current_reward else ""
        if rotation:
            cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(self.font_body)
            cb.add_text(f"当前轮回: {rotation}", 35, 55)

        y_offset = 60 if not rotation else 85
        if essences:
            cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(self.font_small)
            cb.add_text("钢铁精华兑换:", 25, y_offset)
            y_offset += 25

            for i, e in enumerate(essences):
                bg_color = ThemeColor.BG_CARD if i % 2 == 0 else ThemeColor.BG_CARD_ALT
                cb.draw_rounded_rect(20, y_offset, 760, 45, radius=6, fill=bg_color)

                cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(self.font_body)
                cb.add_text(e.name, 35, y_offset + 8)
                cb.set_color(ThemeColor.ACCENT_GOLD).set_font(self.font_small)
                cb.add_text(f"{e.cost} 钢铁精华", 640, y_offset + 8)

                y_offset += item_height

        return cb.to_image()

    def create_nightwave_card(self, nightwave: SeasonInfo) -> Image.Image:
        """绘制午夜电波卡片。

        Args:
            nightwave: SeasonInfo 模型。
        """
        card_width = 800
        item_height = 50
        card_height = 80 + len(nightwave.active_challenges) * item_height + 20

        cb = ImageCombiner(card_width, max(card_height, 150), ThemeColor.BG_DARK)

        cb.set_color(ThemeColor.ACCENT_BLUE).set_font(self.font_title)
        cb.add_text("📡 午夜电波", 25, 15)

        season = str(nightwave.season) if nightwave.season else ""
        if season:
            cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(self.font_small)
            cb.add_text(f"第 {season} 季", 640, 15)

        cb.draw_line(25, 48, 775, 48, width=2)

        y_offset = 85
        if nightwave.active_challenges:
            for i, ac in enumerate(nightwave.active_challenges):
                bg_color = ThemeColor.BG_CARD if i % 2 == 0 else ThemeColor.BG_CARD_ALT
                cb.draw_rounded_rect(20, y_offset, 760, 42, radius=6, fill=bg_color)

                title = ac.name or ac.challenge or "未知任务"
                standing = ac.standing or 0
                is_daily = ac.daily or False
                is_elite = ac.elite or False

                prefix = "🔥 " if is_elite else ("📅 " if is_daily else "")
                cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(self.font_small)
                cb.add_text(f"{prefix}{title}", 35, y_offset + 8)

                label = "精英" if is_elite else ("日常" if is_daily else "周常")
                label_color = ThemeColor.ACCENT_GOLD if is_elite else ThemeColor.TEXT_SECONDARY
                cb.set_color(label_color).set_font(self.font_tiny)
                cb.add_text(f"{standing} 声望  [{label}]", 640, y_offset + 8)

                y_offset += item_height

        return cb.to_image()

    def create_relic_card(self, relics: list[dict]) -> Image.Image:
        """绘制遗物信息卡片。"""
        card_width = 800
        item_height = 50
        card_height = 60 + len(relics) * item_height + 20

        cb = ImageCombiner(card_width, max(card_height, 150), ThemeColor.BG_DARK)

        cb.set_color(ThemeColor.ACCENT_GOLD).set_font(self.font_title)
        cb.add_text("💎 当前遗物掉落", 25, 15)
        cb.draw_line(25, 48, 775, 48, width=2)

        y_offset = 65
        for i, relic in enumerate(relics):
            bg_color = ThemeColor.BG_CARD if i % 2 == 0 else ThemeColor.BG_CARD_ALT
            cb.draw_rounded_rect(20, y_offset, 760, 42, radius=6, fill=bg_color)

            name = relic.get("name", "未知遗物")
            tier = relic.get("tier", "")
            relics_name = relic.get("relic_name", "")

            display = f"{relics_name}" if relics_name else name
            if tier:
                display = f"{display} [{tier}]"

            cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(self.font_body)
            cb.add_text(display, 35, y_offset + 8)

            eta = relic.get("eta", "")
            if eta:
                cb.set_color(ThemeColor.ACCENT).set_font(self.font_small)
                cb.add_text(eta, 640, y_offset + 8)

            y_offset += item_height

        return cb.to_image()

    def create_duviri_card(self, duviri: dict) -> Image.Image:
        """绘制双衍王境信息卡片。"""
        card_width = 800
        card_height = 220

        cb = ImageCombiner(card_width, card_height, ThemeColor.BG_DARK)

        cb.set_color(ThemeColor.ACCENT_GREEN).set_font(self.font_title)
        cb.add_text("🏞 双衍王境", 25, 15)
        cb.draw_line(25, 48, 775, 48, width=2)

        state = duviri.get("state", "未知")
        is_day = duviri.get("is_day", None)
        time_left = duviri.get("time_left", "")

        if is_day is not None:
            state_text = "☀ 白天 (漂泊者)" if is_day else "🌙 夜晚 (指挥官)"
            state_color = ThemeColor.ACCENT_GOLD if is_day else ThemeColor.INFO
        else:
            state_text = state
            state_color = ThemeColor.TEXT_SECONDARY

        cb.set_color(state_color).set_font(self.font_body)
        cb.add_text(f"当前状态: {state_text}", 35, 70)

        if time_left:
            cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(self.font_small)
            cb.add_text(f"剩余时间: {time_left}", 35, 105)

        spiral = duviri.get("spiral", "")
        if spiral:
            cb.set_color(ThemeColor.ACCENT_GOLD).set_font(self.font_small)
            cb.add_text(f"螺旋: {spiral}", 35, 140)

        commander = duviri.get("commander", "")
        if commander:
            cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(self.font_small)
            cb.add_text(f"指挥官: {commander}", 35, 170)

        return cb.to_image()

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
