"""遗物卡片渲染器

采用 3 列卡片网格布局，镜像 Java DefaultDrawRelicsImage.java：
  - 每卡使用独立 ImageCombiner 子画布（卡片内文字居中）
  - 遗物名称居中 + 奖励列表稀有度着色
  - 双层边框 + 看板娘立绘 + 底部署名

与 card_season_info / card_fissures / card_invasions 保持统一色彩主题。
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PIL import ImageFont

from ..wenum.rarity import RarityEnum
from .draw_constant import LayoutConstants, ThemeColor
from .font_manager import FontManager
from .image_combiner import ImageCombiner
from .standing import draw_standing_at

if TYPE_CHECKING:
    from PIL import Image

    from ..model.export.relics import Relics
    from .card_renderer import CardRenderer


# ---------------------------------------------------------------------------
# 布局常量
# ---------------------------------------------------------------------------

_CANVAS_W = 1900
_CONTENT_X, _CONTENT_W = LayoutConstants.get_content_bounds(_CANVAS_W)

_COLS = 3
_COL_GAP = 20
_CARD_W = (_CONTENT_W - (_COLS - 1) * _COL_GAP) // _COLS  # 580
_CARD_H = 480
_CARD_RADIUS = 14
_CARD_PAD = 20
_ROW_GAP = 16

_COL_X = (
    _CONTENT_X,                                          # Col 0: 60
    _CONTENT_X + _CARD_W + _COL_GAP,                     # Col 1: 660
    _CONTENT_X + 2 * (_CARD_W + _COL_GAP),               # Col 2: 1260
)

_TITLE_Y = 60
_CONTENT_START_Y = 175
_FOOTER_OFFSET = 50

# 看板娘尺寸（等比放大，_STANDING_H 略大于 _CARD_H 使立绘自然延伸）
_STANDING_W = 360
_STANDING_H = 530

# 奖励稀有度颜色（镜像 Java getRarityColor）
_RARITY_COLORS: dict[str, tuple[int, int, int]] = {
    "COMMON": ThemeColor.VOID_T2,       # #75562B 棕色
    "UNCOMMON": ThemeColor.VOID_T3,     # #B3B3B3 银色
    "RARE": ThemeColor.VOID_T4,         # #C1BE39 金色
    "LEGENDARY": ThemeColor.ACCENT_GOLD,
}


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _rarity_sort_order(rarity_str: str | None) -> int:
    """稀有度排序权重：Common(0) → Uncommon(1) → Rare(2) → Legendary(3)。"""
    if not rarity_str:
        return 99
    try:
        return RarityEnum[rarity_str].tier
    except (KeyError, ValueError):
        return RarityEnum.from_en_name(rarity_str).tier


def _get_rarity_color(rarity_str: str | None) -> tuple[int, int, int]:
    """将稀有度字符串映射为显示颜色。"""
    if not rarity_str:
        return ThemeColor.TEXT_SECONDARY
    return _RARITY_COLORS.get(rarity_str.upper(), ThemeColor.TEXT_SECONDARY)


def _draw_one_relic_card(
    relic: Relics,
    name_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    reward_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> Image.Image:
    """绘制单张遗物卡片 — 使用独立 ImageCombiner 子画布。

    镜像 Java drawRelicCard()：每卡独立画布 → 叠加到主画布。
    卡片内文字使用 add_centered_text 自然居中。

    Args:
        relic: Relics 模型对象（含 prefetch 的 relic_rewards）。
        name_font: 名称字体。
        reward_font: 奖励字体。

    Returns:
        PIL Image 对象（_CARD_W × _CARD_H）。
    """
    card_cb = ImageCombiner(_CARD_W, _CARD_H, ThemeColor.BG_CARD)

    # 圆角边框（直接使用 Pillow API，绕开 ImageCombiner 的 fill=None→白色回退 bug）
    card_cb._draw.rounded_rectangle(
        [(0, 0), (_CARD_W - 1, _CARD_H - 1)],
        radius=_CARD_RADIUS,
        fill=None,
        outline=ThemeColor.DIVIDER,
        width=2,
    )

    # 遗物名称（居中）
    name = relic.name or relic.uniqueName or "未知遗物"
    card_cb.set_color(ThemeColor.ACCENT_GOLD).set_font(name_font)
    card_cb.add_centered_text(name, 55)

    # 奖励列表（铜→银→金，每行 55px，稀有度着色）
    rewards = sorted(
        relic.relic_rewards,
        key=lambda r: (_rarity_sort_order(r.rarity), r.rewardName or ""),
    )
    reward_y = 115
    for reward in rewards:
        reward_name = reward.get_reward_name()
        rarity_color = _get_rarity_color(reward.rarity)
        card_cb.set_color(rarity_color).set_font(reward_font)
        card_cb.add_centered_text(reward_name, reward_y)
        reward_y += 55

    return card_cb.to_image()


# ---------------------------------------------------------------------------
# 主渲染函数
# ---------------------------------------------------------------------------

def render_relic_card(
    renderer: CardRenderer,
    relics: list[Relics],
) -> Image.Image:
    """绘制遗物信息卡片 — 3 列网格 + 双层边框 + 看板娘 + 底部署名。

    Args:
        renderer: CardRenderer 实例。
        relics: Relics 模型列表（已 prefetch relic_rewards）。

    Returns:
        PIL Image 对象。
    """
    if not relics:
        return renderer.create_text_image("未找到遗物数据", 800, 120)

    # ---- 字体 ----
    title_font = FontManager.get_text_font(64)
    name_font = FontManager.get_text_font(42)
    reward_font = FontManager.get_text_font(32)
    FontManager.get_text_font(26)

    # ---- 布局计算 ----
    n = len(relics)
    rows = math.ceil(n / _COLS)
    last_row_full = n % _COLS == 0

    # 看板娘始终在 Col 2：末行满则追加占位行
    if last_row_full:
        total_rows = rows + 1
        standing_card_row = rows
    else:
        total_rows = rows
        standing_card_row = rows - 1

    cards_h = total_rows * _CARD_H + (total_rows - 1) * _ROW_GAP
    content_end = _CONTENT_START_Y + cards_h
    canvas_h = max(content_end + _FOOTER_OFFSET + 30, 600)

    # ---- 画布 ----
    cb = ImageCombiner(_CANVAS_W, canvas_h, ThemeColor.BG_DARK)

    # ---- 双层边框 ----
    cb.draw_default_double_border()

    # ---- 标题 ----
    cb.set_color(ThemeColor.ACCENT_GOLD).set_font(title_font)
    cb.add_centered_text("遗物查询", _TITLE_Y)

    # ---- 分割线 ----
    cb.draw_content_divider(_TITLE_Y + 68, _CONTENT_X, _CONTENT_W)

    # ---- 遗物卡片（3 列网格） ----
    for i, relic in enumerate(relics):
        row = i // _COLS
        col = i % _COLS
        card_x = _COL_X[col]
        card_y = _CONTENT_START_Y + row * (_CARD_H + _ROW_GAP)
        card_img = _draw_one_relic_card(relic, name_font, reward_font)
        cb.draw_image(card_img, card_x, card_y)

    # ---- 看板娘（始终在 Col 2 位置） ----
    standing_x = _COL_X[2] + (_CARD_W - _STANDING_W) // 2
    standing_y = _CONTENT_START_Y + standing_card_row * (_CARD_H + _ROW_GAP)
    draw_standing_at(cb, standing_x, standing_y, _STANDING_W, _STANDING_H)

    # ---- 底部署名 ----
    cb.draw_card_footer(canvas_h, _FOOTER_OFFSET, 26)

    return cb.to_image()
