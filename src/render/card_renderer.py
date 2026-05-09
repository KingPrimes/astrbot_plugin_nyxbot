"""Card renderer — Pillow 信息卡片渲染器（主引擎）

基于 Pillow 直接绘制 Warframe 信息卡片，优先保证速度与视觉效果。
设计原则：
- 每张卡片一次性绘制完成，避免多次合成
- 使用预定义配色模板，确保视觉一致性
- 记录渲染耗时，便于后续性能优化
"""
from __future__ import annotations

import io
import time
from pathlib import Path
from typing import Any, Optional

from PIL import Image, ImageDraw, ImageFont


class CardRenderer:
    """Pillow 信息卡片渲染器 — 优先保证速度与视觉效果。

    所有 Warframe 信息卡片（警报、突击、裂隙等）均由本渲染器统一绘制。
    """

    # Warframe 主题色板
    COLORS = {
        "bg_dark": (26, 26, 46),          # #1a1a2e
        "bg_card": (22, 33, 62),          # #16213e
        "bg_card_alt": (30, 45, 80),      # 交替卡片背景
        "accent": (233, 69, 96),          # #e94560
        "accent_blue": (69, 133, 233),    # 蓝色强调
        "accent_green": (69, 233, 150),   # 绿色强调
        "accent_gold": (255, 215, 0),     # 金色
        "text_primary": (255, 255, 255),
        "text_secondary": (170, 170, 170),
        "text_muted": (120, 120, 120),
        "reward_bg": (15, 52, 96),        # 奖励标签背景
        "divider": (60, 60, 90),          # 分割线
        "success": (69, 233, 150),
        "warning": (255, 193, 7),
        "danger": (233, 69, 96),
        "info": (69, 133, 233),
    }

    def __init__(self, font_path: str | None = None):
        self.font_path = font_path or self._find_font()
        self._load_fonts()

    def _load_fonts(self):
        """加载字体。"""
        self.font_title = ImageFont.truetype(self.font_path, 26)
        self.font_subtitle = ImageFont.truetype(self.font_path, 20)
        self.font_body = ImageFont.truetype(self.font_path, 16)
        self.font_small = ImageFont.truetype(self.font_path, 13)
        self.font_tiny = ImageFont.truetype(self.font_path, 11)

    def _find_font(self) -> str:
        """查找中文字体，回退到系统字体。"""
        # 优先使用项目内置字体
        script_dir = Path(__file__).parent
        candidates = [
            str(script_dir / "fonts" / "SourceHanSerifCN-Bold.ttf"),
            "C:/Windows/Fonts/msyh.ttc",       # 微软雅黑
            "C:/Windows/Fonts/simhei.ttf",     # 黑体
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # Linux 文泉驿
            "/System/Library/Fonts/PingFang.ttc",               # macOS 苹方
        ]
        for path in candidates:
            if Path(path).exists():
                return str(Path(path).resolve())
        # 没有找到字体文件，抛出异常
        raise FileNotFoundError("未找到中文字体，请安装字体文件")

    # ========================================================================
    # 卡片绘制方法
    # ========================================================================

    def create_alert_card(self, alerts: list[dict]) -> Image.Image:
        """绘制警报信息卡片。

        Args:
            alerts: 警报数据列表，每个元素包含 node, mission_type, faction,
                    min_level, max_level, rewards, eta 等字段。

        Returns:
            PIL Image 对象。
        """
        t0 = time.perf_counter()
        card_width = 800
        item_height = 110
        padding_top = 60
        card_height = padding_top + len(alerts) * item_height + 20

        img = Image.new("RGB", (card_width, max(card_height, 200)), self.COLORS["bg_dark"])
        draw = ImageDraw.Draw(img)

        # 标题栏
        draw.text((25, 15), "⚠ 当前警报", fill=self.COLORS["accent"], font=self.font_title)
        draw.line([(25, 48), (775, 48)], fill=self.COLORS["accent"], width=2)

        y_offset = 65
        for i, alert in enumerate(alerts):
            bg_color = self.COLORS["bg_card"] if i % 2 == 0 else self.COLORS["bg_card_alt"]
            draw.rounded_rectangle(
                [(20, y_offset), (780, y_offset + 100)],
                radius=8, fill=bg_color,
            )

            # 任务节点名称
            node_name = alert.get("node", "未知节点")
            draw.text((35, y_offset + 10), node_name, fill=self.COLORS["text_primary"], font=self.font_body)

            # 任务类型 | 派系
            mission_type = alert.get("mission_type", "未知任务")
            faction = alert.get("faction", "未知派系")
            draw.text(
                (35, y_offset + 38),
                f"{mission_type}  |  {faction}",
                fill=self.COLORS["text_secondary"],
                font=self.font_small,
            )

            # 等级范围
            min_lv = alert.get("min_level", "?")
            max_lv = alert.get("max_level", "?")
            draw.text(
                (640, y_offset + 10),
                f"Lv.{min_lv} - {max_lv}",
                fill=self.COLORS["text_muted"],
                font=self.font_small,
            )

            # 倒计时
            eta = alert.get("eta", "")
            if eta:
                draw.text(
                    (640, y_offset + 35),
                    eta,
                    fill=self.COLORS["accent_gold"],
                    font=self.font_small,
                )

            # 奖励标签
            rewards = alert.get("rewards", [])
            x_reward = 35
            for item_name in rewards[:6]:  # 最多显示6个奖励
                # 计算文字宽度，自适应标签大小
                bbox = draw.textbbox((0, 0), item_name, font=self.font_tiny)
                tag_w = bbox[2] - bbox[0] + 16
                tag_h = 22
                draw.rounded_rectangle(
                    [(x_reward, y_offset + 65), (x_reward + tag_w, y_offset + 65 + tag_h)],
                    radius=4, fill=self.COLORS["reward_bg"],
                )
                draw.text(
                    (x_reward + 8, y_offset + 67),
                    item_name,
                    fill=self.COLORS["text_secondary"],
                    font=self.font_tiny,
                )
                x_reward += tag_w + 8

            y_offset += item_height

        elapsed = time.perf_counter() - t0
        # 可在调试时启用
        # print(f"[性能] 警报卡片渲染耗时: {elapsed*1000:.1f}ms")
        return img

    def create_sortie_card(self, sorties: list[dict]) -> Image.Image:
        """绘制突击信息卡片。"""
        t0 = time.perf_counter()
        card_width = 800
        item_height = 130
        card_height = 60 + len(sorties) * item_height + 20

        img = Image.new("RGB", (card_width, max(card_height, 200)), self.COLORS["bg_dark"])
        draw = ImageDraw.Draw(img)

        draw.text((25, 15), "⚡ 今日突击", fill=self.COLORS["accent_gold"], font=self.font_title)
        draw.line([(25, 48), (775, 48)], fill=self.COLORS["accent_gold"], width=2)

        y_offset = 65
        for i, sortie in enumerate(sorties):
            bg_color = self.COLORS["bg_card"] if i % 2 == 0 else self.COLORS["bg_card_alt"]
            draw.rounded_rectangle(
                [(20, y_offset), (780, y_offset + 115)],
                radius=8, fill=bg_color,
            )

            # 阶段标题
            variant = sortie.get("variant", f"阶段 {i + 1}")
            modifier = sortie.get("modifier", "")
            draw.text((35, y_offset + 10), variant, fill=self.COLORS["accent_blue"], font=self.font_subtitle)

            # 任务节点
            node = sortie.get("node", "未知节点")
            mission_type = sortie.get("mission_type", "未知任务")
            draw.text(
                (35, y_offset + 40),
                f"{node}  —  {mission_type}",
                fill=self.COLORS["text_primary"],
                font=self.font_body,
            )

            # 派系
            faction = sortie.get("faction", "")
            if faction:
                draw.text(
                    (640, y_offset + 40),
                    faction,
                    fill=self.COLORS["text_secondary"],
                    font=self.font_small,
                )

            # 特殊规则（modifier description）
            if modifier:
                draw.text(
                    (35, y_offset + 70),
                    f"规则: {modifier}",
                    fill=self.COLORS["accent_gold"],
                    font=self.font_small,
                )

            y_offset += item_height

        elapsed = time.perf_counter() - t0
        return img

    def create_fissure_card(self, fissures: list[dict]) -> Image.Image:
        """绘制裂隙信息卡片。"""
        t0 = time.perf_counter()
        card_width = 800
        item_height = 80
        card_height = 60 + len(fissures) * item_height + 20

        img = Image.new("RGB", (card_width, max(card_height, 200)), self.COLORS["bg_dark"])
        draw = ImageDraw.Draw(img)

        draw.text((25, 15), "🌀 当前裂隙", fill=self.COLORS["info"], font=self.font_title)
        draw.line([(25, 48), (775, 48)], fill=self.COLORS["info"], width=2)

        y_offset = 65
        # 按等级分组：不朽/无瑕/光辉/幻影
        tier_order = {4: 0, 3: 1, 2: 2, 1: 3}
        sorted_fissures = sorted(fissures, key=lambda f: tier_order.get(f.get("tier", 0), 5))

        for i, fissure in enumerate(sorted_fissures):
            bg_color = self.COLORS["bg_card"] if i % 2 == 0 else self.COLORS["bg_card_alt"]
            draw.rounded_rectangle(
                [(20, y_offset), (780, y_offset + 68)],
                radius=8, fill=bg_color,
            )

            # 节点 + 任务类型
            node = fissure.get("node", "未知节点")
            mission_type = fissure.get("mission_type", "未知")
            draw.text(
                (35, y_offset + 10),
                f"{node}  [{mission_type}]",
                fill=self.COLORS["text_primary"],
                font=self.font_body,
            )

            # 裂隙等级
            tier_name = fissure.get("tier_name", "")
            if tier_name:
                draw.text(
                    (35, y_offset + 38),
                    tier_name,
                    fill=self.COLORS["accent"],
                    font=self.font_small,
                )

            # 派系
            faction = fissure.get("faction", "")
            if faction:
                draw.text(
                    (640, y_offset + 10),
                    faction,
                    fill=self.COLORS["text_secondary"],
                    font=self.font_small,
                )

            # 倒计时
            eta = fissure.get("eta", "")
            if eta:
                draw.text(
                    (640, y_offset + 38),
                    eta,
                    fill=self.COLORS["accent_gold"],
                    font=self.font_small,
                )

            y_offset += item_height

        elapsed = time.perf_counter() - t0
        return img

    def create_invasion_card(self, invasions: list[dict]) -> Image.Image:
        """绘制入侵信息卡片。"""
        t0 = time.perf_counter()
        card_width = 800
        item_height = 100
        card_height = 60 + len(invasions) * item_height + 20

        img = Image.new("RGB", (card_width, max(card_height, 200)), self.COLORS["bg_dark"])
        draw = ImageDraw.Draw(img)

        draw.text((25, 15), "⚔ 当前入侵", fill=self.COLORS["warning"], font=self.font_title)
        draw.line([(25, 48), (775, 48)], fill=self.COLORS["warning"], width=2)

        y_offset = 65
        for i, invasion in enumerate(invasions):
            bg_color = self.COLORS["bg_card"] if i % 2 == 0 else self.COLORS["bg_card_alt"]
            draw.rounded_rectangle(
                [(20, y_offset), (780, y_offset + 88)],
                radius=8, fill=bg_color,
            )

            # 节点
            node = invasion.get("node", "未知节点")
            draw.text((35, y_offset + 10), node, fill=self.COLORS["text_primary"], font=self.font_body)

            # 进攻方 vs 防守方
            attacker = invasion.get("attacker", "")
            defender = invasion.get("defender", "")
            draw.text(
                (35, y_offset + 38),
                f"{attacker}  ⚔  {defender}",
                fill=self.COLORS["text_secondary"],
                font=self.font_small,
            )

            # 进度
            completion = invasion.get("completion", 0)
            progress_color = self.COLORS["success"] if completion > 50 else self.COLORS["warning"]
            draw.text(
                (640, y_offset + 10),
                f"进度: {completion:.1f}%",
                fill=progress_color,
                font=self.font_small,
            )

            # 奖励
            reward = invasion.get("reward", "")
            if reward:
                draw.text(
                    (640, y_offset + 38),
                    f"奖励: {reward}",
                    fill=self.COLORS["accent_gold"],
                    font=self.font_tiny,
                )

            y_offset += item_height

        elapsed = time.perf_counter() - t0
        return img

    def create_void_trader_card(self, trader: dict) -> Image.Image:
        """绘制虚空商人信息卡片。"""
        t0 = time.perf_counter()
        card_width = 800
        inventory = trader.get("inventory", [])
        item_height = 55
        card_height = 80 + len(inventory) * item_height + 20

        img = Image.new("RGB", (card_width, max(card_height, 200)), self.COLORS["bg_dark"])
        draw = ImageDraw.Draw(img)

        # 标题
        trader_name = trader.get("name", "Baro Ki'Teer")
        location = trader.get("location", "未知中继站")
        draw.text((25, 15), f"🏪 虚空商人 - {trader_name}", fill=self.COLORS["accent_gold"], font=self.font_title)
        draw.text((25, 42), f"位置: {location}", fill=self.COLORS["text_secondary"], font=self.font_small)

        eta = trader.get("eta", "")
        if eta:
            draw.text((640, 42), f"剩余: {eta}", fill=self.COLORS["accent"], font=self.font_small)

        draw.line([(25, 68), (775, 68)], fill=self.COLORS["accent_gold"], width=2)

        y_offset = 82
        for i, item in enumerate(inventory):
            bg_color = self.COLORS["bg_card"] if i % 2 == 0 else self.COLORS["bg_card_alt"]
            draw.rounded_rectangle(
                [(20, y_offset), (780, y_offset + 45)],
                radius=6, fill=bg_color,
            )

            item_name = item.get("name", "未知物品")
            ducats = item.get("ducats", 0)
            credits = item.get("credits", 0)

            draw.text((35, y_offset + 8), item_name, fill=self.COLORS["text_primary"], font=self.font_body)
            draw.text(
                (500, y_offset + 8),
                f"{ducats}  ducats  |  {credits:,}  credits",
                fill=self.COLORS["accent_gold"],
                font=self.font_small,
            )

            y_offset += item_height

        elapsed = time.perf_counter() - t0
        return img

    def create_arbitration_card(self, arbitration: dict) -> Image.Image:
        """绘制仲裁信息卡片。"""
        t0 = time.perf_counter()
        card_width = 800
        card_height = 200

        img = Image.new("RGB", (card_width, card_height), self.COLORS["bg_dark"])
        draw = ImageDraw.Draw(img)

        draw.text((25, 15), "🏅 当前仲裁", fill=self.COLORS["accent_gold"], font=self.font_title)
        draw.line([(25, 48), (775, 48)], fill=self.COLORS["accent_gold"], width=2)

        node = arbitration.get("node", "未知节点")
        mission_type = arbitration.get("mission_type", "未知任务")
        faction = arbitration.get("faction", "未知派系")

        draw.text((35, 70), node, fill=self.COLORS["text_primary"], font=self.font_body)
        draw.text(
            (35, 100),
            f"{mission_type}  |  {faction}",
            fill=self.COLORS["text_secondary"],
            font=self.font_small,
        )

        eta = arbitration.get("eta", "")
        if eta:
            draw.text((640, 70), f"剩余: {eta}", fill=self.COLORS["accent"], font=self.font_small)

        elapsed = time.perf_counter() - t0
        return img

    def create_cycle_card(self, cycles: list[dict], title: str = "平原周期") -> Image.Image:
        """绘制周期信息卡片（希图斯/金星/扎里曼等）。

        Args:
            cycles: 周期数据列表，每个元素包含 name, state, time_left, is_day 等字段。
            title: 卡片标题。
        """
        t0 = time.perf_counter()
        card_width = 800
        item_height = 70
        card_height = 60 + len(cycles) * item_height + 20

        img = Image.new("RGB", (card_width, max(card_height, 150)), self.COLORS["bg_dark"])
        draw = ImageDraw.Draw(img)

        draw.text((25, 15), f"🌍 {title}", fill=self.COLORS["accent_green"], font=self.font_title)
        draw.line([(25, 48), (775, 48)], fill=self.COLORS["accent_green"], width=2)

        y_offset = 65
        for i, cycle in enumerate(cycles):
            bg_color = self.COLORS["bg_card"] if i % 2 == 0 else self.COLORS["bg_card_alt"]
            draw.rounded_rectangle(
                [(20, y_offset), (780, y_offset + 58)],
                radius=8, fill=bg_color,
            )

            name = cycle.get("name", "未知")
            state = cycle.get("state", "未知")
            is_day = cycle.get("is_day", None)
            time_left = cycle.get("time_left", "")

            # 状态指示器
            if is_day is not None:
                state_color = self.COLORS["accent_gold"] if is_day else self.COLORS["info"]
                state_icon = "☀ 白天" if is_day else "🌙 夜晚"
            else:
                state_color = self.COLORS["text_secondary"]
                state_icon = state

            draw.text((35, y_offset + 8), name, fill=self.COLORS["text_primary"], font=self.font_body)
            draw.text(
                (35, y_offset + 33),
                f"状态: {state_icon}",
                fill=state_color,
                font=self.font_small,
            )

            if time_left:
                draw.text(
                    (640, y_offset + 8),
                    f"剩余: {time_left}",
                    fill=self.COLORS["accent"],
                    font=self.font_small,
                )

            y_offset += item_height

        elapsed = time.perf_counter() - t0
        return img

    def create_daily_deals_card(self, deals: list[dict]) -> Image.Image:
        """绘制每日特惠卡片。"""
        t0 = time.perf_counter()
        card_width = 800
        item_height = 65
        card_height = 60 + len(deals) * item_height + 20

        img = Image.new("RGB", (card_width, max(card_height, 150)), self.COLORS["bg_dark"])
        draw = ImageDraw.Draw(img)

        draw.text((25, 15), "💰 每日特惠", fill=self.COLORS["accent_gold"], font=self.font_title)
        draw.line([(25, 48), (775, 48)], fill=self.COLORS["accent_gold"], width=2)

        y_offset = 65
        for i, deal in enumerate(deals):
            bg_color = self.COLORS["bg_card"] if i % 2 == 0 else self.COLORS["bg_card_alt"]
            draw.rounded_rectangle(
                [(20, y_offset), (780, y_offset + 54)],
                radius=8, fill=bg_color,
            )

            item_name = deal.get("item", "未知物品")
            original = deal.get("original_price", 0)
            sale = deal.get("sale_price", 0)
            discount = deal.get("discount", 0)
            total = deal.get("total", 0)
            sold = deal.get("sold", 0)

            draw.text((35, y_offset + 8), item_name, fill=self.COLORS["text_primary"], font=self.font_body)

            # 折扣率
            if discount > 0:
                draw.text(
                    (400, y_offset + 8),
                    f"-{discount}%",
                    fill=self.COLORS["accent"],
                    font=self.font_body,
                )

            # 价格信息
            draw.text(
                (500, y_offset + 8),
                f"原价 {original}p  → 特价 {sale}p",
                fill=self.COLORS["accent_gold"],
                font=self.font_small,
            )

            # 库存
            if total > 0:
                remaining = total - sold
                draw.text(
                    (500, y_offset + 30),
                    f"剩余 {remaining}/{total}",
                    fill=self.COLORS["text_secondary"],
                    font=self.font_tiny,
                )

            y_offset += item_height

        elapsed = time.perf_counter() - t0
        return img

    def create_steel_path_card(self, steel_path: dict) -> Image.Image:
        """绘制钢铁之路卡片。"""
        t0 = time.perf_counter()
        card_width = 800
        essences = steel_path.get("essences", [])
        item_height = 55
        card_height = 80 + len(essences) * item_height + 20

        img = Image.new("RGB", (card_width, max(card_height, 180)), self.COLORS["bg_dark"])
        draw = ImageDraw.Draw(img)

        draw.text((25, 15), "⚔ 钢铁之路", fill=self.COLORS["accent"], font=self.font_title)
        draw.line([(25, 48), (775, 48)], fill=self.COLORS["accent"], width=2)

        # 当前轮回
        rotation = steel_path.get("rotation", "")
        if rotation:
            draw.text((35, 55), f"当前轮回: {rotation}", fill=self.COLORS["text_primary"], font=self.font_body)

        y_offset = 60 if not rotation else 85
        if essences:
            draw.text((25, y_offset), "钢铁精华兑换:", fill=self.COLORS["text_secondary"], font=self.font_small)
            y_offset += 25

            for i, essence in enumerate(essences):
                bg_color = self.COLORS["bg_card"] if i % 2 == 0 else self.COLORS["bg_card_alt"]
                draw.rounded_rectangle(
                    [(20, y_offset), (780, y_offset + 45)],
                    radius=6, fill=bg_color,
                )

                name = essence.get("name", "未知物品")
                cost = essence.get("cost", 0)

                draw.text((35, y_offset + 8), name, fill=self.COLORS["text_primary"], font=self.font_body)
                draw.text(
                    (640, y_offset + 8),
                    f"{cost} 钢铁精华",
                    fill=self.COLORS["accent_gold"],
                    font=self.font_small,
                )

                y_offset += item_height

        elapsed = time.perf_counter() - t0
        return img

    def create_nightwave_card(self, nightwave: dict) -> Image.Image:
        """绘制午夜电波卡片。"""
        t0 = time.perf_counter()
        card_width = 800
        challenges = nightwave.get("challenges", [])
        item_height = 50
        card_height = 80 + len(challenges) * item_height + 20

        img = Image.new("RGB", (card_width, max(card_height, 150)), self.COLORS["bg_dark"])
        draw = ImageDraw.Draw(img)

        draw.text((25, 15), "📡 午夜电波", fill=self.COLORS["accent_blue"], font=self.font_title)

        # 电波等级
        season = nightwave.get("season", "")
        rank = nightwave.get("rank", 0)
        if season:
            draw.text((640, 15), f"第 {season} 季", fill=self.COLORS["text_secondary"], font=self.font_small)

        draw.line([(25, 48), (775, 48)], fill=self.COLORS["accent_blue"], width=2)

        if rank is not None:
            draw.text((25, 55), f"当前等级: {rank}", fill=self.COLORS["text_primary"], font=self.font_body)

        y_offset = 85
        if challenges:
            for i, challenge in enumerate(challenges):
                bg_color = self.COLORS["bg_card"] if i % 2 == 0 else self.COLORS["bg_card_alt"]
                draw.rounded_rectangle(
                    [(20, y_offset), (780, y_offset + 42)],
                    radius=6, fill=bg_color,
                )

                title = challenge.get("title", "未知任务")
                standing = challenge.get("standing", 0)
                is_daily = challenge.get("is_daily", False)
                is_elite = challenge.get("is_elite", False)

                prefix = "🔥 " if is_elite else ("📅 " if is_daily else "")
                draw.text((35, y_offset + 8), f"{prefix}{title}", fill=self.COLORS["text_primary"], font=self.font_small)

                label = "精英" if is_elite else ("日常" if is_daily else "周常")
                draw.text(
                    (640, y_offset + 8),
                    f"{standing} 声望  [{label}]",
                    fill=self.COLORS["accent_gold"] if is_elite else self.COLORS["text_secondary"],
                    font=self.font_tiny,
                )

                y_offset += item_height

        elapsed = time.perf_counter() - t0
        return img

    def create_relic_card(self, relics: list[dict]) -> Image.Image:
        """绘制遗物信息卡片。"""
        t0 = time.perf_counter()
        card_width = 800
        item_height = 50
        card_height = 60 + len(relics) * item_height + 20

        img = Image.new("RGB", (card_width, max(card_height, 150)), self.COLORS["bg_dark"])
        draw = ImageDraw.Draw(img)

        draw.text((25, 15), "💎 当前遗物掉落", fill=self.COLORS["accent_gold"], font=self.font_title)
        draw.line([(25, 48), (775, 48)], fill=self.COLORS["accent_gold"], width=2)

        y_offset = 65
        for i, relic in enumerate(relics):
            bg_color = self.COLORS["bg_card"] if i % 2 == 0 else self.COLORS["bg_card_alt"]
            draw.rounded_rectangle(
                [(20, y_offset), (780, y_offset + 42)],
                radius=6, fill=bg_color,
            )

            name = relic.get("name", "未知遗物")
            tier = relic.get("tier", "")
            relics_name = relic.get("relic_name", "")

            display = f"{relics_name}" if relics_name else name
            if tier:
                display = f"{display} [{tier}]"

            draw.text((35, y_offset + 8), display, fill=self.COLORS["text_primary"], font=self.font_body)

            eta = relic.get("eta", "")
            if eta:
                draw.text(
                    (640, y_offset + 8),
                    eta,
                    fill=self.COLORS["accent"],
                    font=self.font_small,
                )

            y_offset += item_height

        elapsed = time.perf_counter() - t0
        return img

    def create_duviri_card(self, duviri: dict) -> Image.Image:
        """绘制双衍王境信息卡片。"""
        t0 = time.perf_counter()
        card_width = 800
        card_height = 220

        img = Image.new("RGB", (card_width, card_height), self.COLORS["bg_dark"])
        draw = ImageDraw.Draw(img)

        draw.text((25, 15), "🏞 双衍王境", fill=self.COLORS["accent_green"], font=self.font_title)
        draw.line([(25, 48), (775, 48)], fill=self.COLORS["accent_green"], width=2)

        # 周期状态
        state = duviri.get("state", "未知")
        is_day = duviri.get("is_day", None)
        time_left = duviri.get("time_left", "")

        if is_day is not None:
            state_text = "☀ 白天 (漂泊者)" if is_day else "🌙 夜晚 (指挥官)"
            state_color = self.COLORS["accent_gold"] if is_day else self.COLORS["info"]
        else:
            state_text = state
            state_color = self.COLORS["text_secondary"]

        draw.text((35, 70), f"当前状态: {state_text}", fill=state_color, font=self.font_body)

        if time_left:
            draw.text((35, 105), f"剩余时间: {time_left}", fill=self.COLORS["text_secondary"], font=self.font_small)

        # 可选信息
        spiral = duviri.get("spiral", "")
        if spiral:
            draw.text((35, 140), f"螺旋: {spiral}", fill=self.COLORS["accent_gold"], font=self.font_small)

        commander = duviri.get("commander", "")
        if commander:
            draw.text((35, 170), f"指挥官: {commander}", fill=self.COLORS["text_secondary"], font=self.font_small)

        elapsed = time.perf_counter() - t0
        return img

    # ========================================================================
    # 通用工具
    # ========================================================================

    @staticmethod
    def render_to_bytes(img: Image.Image, fmt: str = "PNG") -> bytes:
        """将 PIL Image 转为 bytes 供 AstrBot 发送。

        Args:
            img: PIL Image 对象。
            fmt: 图片格式（默认 PNG）。

        Returns:
            图片的 bytes 数据。
        """
        buf = io.BytesIO()
        img.save(buf, format=fmt)
        return buf.getvalue()

    @staticmethod
    def create_text_image(text: str, width: int = 600, height: int = 200) -> Image.Image:
        """创建纯文字图片（用于错误提示或简单信息）。

        Args:
            text: 显示的文字。
            width: 图片宽度。
            height: 图片高度。

        Returns:
            PIL Image 对象。
        """
        img = Image.new("RGB", (width, height), (26, 26, 46))
        draw = ImageDraw.Draw(img)
        # 使用默认字体
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)
        except Exception:
            font = ImageFont.load_default()

        # 文字居中
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (width - text_w) // 2
        y = (height - text_h) // 2
        draw.text((x, y), text, fill=(255, 255, 255), font=font)
        return img
