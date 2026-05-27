"""入侵卡片渲染器

采用单列宽卡片布局，镜像 Java DefaultDrawInvasionImage.java：
  - 居中标题 + 双色顶部分割条（进攻/防守按进度比例）
  - 圆角进度条 + 双方阵营对抗展示 + 奖励信息
  - 双层边框 + 看板娘立绘 + 底部署名
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import ImageFont

from .draw_constant import LayoutConstants, ThemeColor
from .font_manager import FontManager
from .image_combiner import ImageCombiner
from .standing import draw_standing_at

if TYPE_CHECKING:
    from PIL import Image

    from ..model.world_state import Invasion
    from .card_renderer import CardRenderer


# ---------------------------------------------------------------------------
# 颜色常量
# ---------------------------------------------------------------------------

_ATTACKER_COLOR: tuple[int, int, int] = (255, 107, 107)   # 进攻方 红色
_DEFENDER_COLOR: tuple[int, int, int] = (76, 175, 80)     # 防守方 绿色

# ---------------------------------------------------------------------------
# 布局常量
# ---------------------------------------------------------------------------

_CANVAS_W = 1300
_CONTENT_X, _CONTENT_W = LayoutConstants.get_content_bounds(_CANVAS_W)

_CARD_W = _CONTENT_W                               # 单列全宽 1180
_CARD_H = 180
_CARD_RADIUS = 14
_CARD_PAD = 24                                     # 卡片内边距
_ROW_GAP = 16

_ACCENT_STRIP_H = 6                                # 顶部分割色条高度

_TITLE_Y = 60
_CONTENT_START_Y = 175
_FOOTER_OFFSET = 50

# 看板娘尺寸
_STANDING_W = 260
_STANDING_H = 390


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _build_progress(count: float | None, goal: float | None) -> float:
    """计算进度百分比 (0.0 ~ 1.0)，镜像 Java Math.abs(count)/goal。"""
    if goal is None or goal == 0 or count is None:
        return 0.0
    return min(abs(count) / goal, 1.0)


def _get_first_reward_text(rewards: list, default: str = "") -> str:
    """从 Reward 列表中提取第一个 counted_item 的显示文本。"""
    for rw in rewards:
        if rw.counted_items:
            item = rw.counted_items[0]
            return f"{item.count}x {item.name}" if item.count and item.name else default
    return default


def _draw_one_invasion_card(
    cb: ImageCombiner,
    invasion: Invasion,
    card_x: int,
    card_y: int,
    renderer: CardRenderer,
    node_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    faction_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    reward_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    progress_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """绘制单张入侵卡片。"""
    inner_x = card_x + _CARD_PAD
    inner_w = _CARD_W - _CARD_PAD * 2

    progress = _build_progress(invasion.count, invasion.goal)

    # 卡片背景
    cb.set_color(ThemeColor.BG_CARD)
    cb.draw_rounded_rect(card_x, card_y, _CARD_W, _CARD_H, radius=_CARD_RADIUS)

    # ---- 顶部分割色条：进攻侧(红) + 防守侧(绿)，按进度比例 ----
    split_x = card_x + int(_CARD_W * progress)
    # 进攻侧（左，红色）
    attacker_strip_w = split_x - card_x
    if attacker_strip_w > _CARD_RADIUS:
        cb.set_color(_ATTACKER_COLOR)
        cb.fill_rect(card_x + _CARD_RADIUS, card_y + 2, attacker_strip_w - _CARD_RADIUS, _ACCENT_STRIP_H)
    # 防守侧（右，绿色）
    defender_strip_w = card_x + _CARD_W - split_x
    if defender_strip_w > _CARD_RADIUS:
        cb.set_color(_DEFENDER_COLOR)
        cb.fill_rect(split_x, card_y + 2, defender_strip_w - _CARD_RADIUS, _ACCENT_STRIP_H)

    # ---- 行 1: 节点名称（左） + 进度百分比（右） ----
    node = invasion.node or "未知节点"
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(node_font)
    cb.add_text(node, inner_x, card_y + 34)

    pct_text = f"进度: {progress * 100:.1f}%"
    cb.set_color(ThemeColor.ACCENT_BLUE).set_font(progress_font)
    pct_w = cb.get_string_width(pct_text)
    cb.add_text(pct_text, inner_x + inner_w - pct_w, card_y + 36)

    # ---- 行 2: 双方阵营对抗（居中） ----
    row2_y = card_y + 82

    # 进攻方
    attacker = invasion.faction
    atk_icon = ""
    atk_name = "未知"
    if attacker is not None:
        atk_icon, atk_color = renderer.resolve_faction_icon_and_color(attacker)
        atk_name = attacker.display_name
    else:
        atk_color = ThemeColor.TEXT_MUTED

    # 防守方
    defender = invasion.defender_faction
    def_icon = ""
    def_name = "未知"
    if defender is not None:
        def_icon, def_color = renderer.resolve_faction_icon_and_color(defender)
        def_name = defender.display_name
    else:
        def_color = ThemeColor.TEXT_MUTED

    # 分隔符
    separator = "  VS  "
    cb.set_font(faction_font)
    sep_w = cb.get_string_width(separator)

    # 计算进攻侧宽度
    atk_w = 0
    if atk_icon and renderer.font_wf_icon:
        cb.set_font(renderer.font_wf_icon)
        atk_w += cb.get_string_width(atk_icon) + 4
    cb.set_font(faction_font)
    atk_w += cb.get_string_width(atk_name)

    # 计算防守侧宽度
    def_w = 0
    if def_icon and renderer.font_wf_icon:
        cb.set_font(renderer.font_wf_icon)
        def_w += cb.get_string_width(def_icon) + 4
    cb.set_font(faction_font)
    def_w += cb.get_string_width(def_name)

    total_w = atk_w + sep_w + def_w
    cursor_x = inner_x + (inner_w - total_w) // 2

    # 进攻方图标 + 名称
    if atk_icon and renderer.font_wf_icon:
        cb.set_color(atk_color).set_font(renderer.font_wf_icon)
        cb.add_text(atk_icon, cursor_x, row2_y - 2)
        cursor_x += cb.get_string_width(atk_icon) + 4
    cb.set_color(atk_color).set_font(faction_font)
    cb.add_text(atk_name, cursor_x, row2_y + 3)
    cursor_x += cb.get_string_width(atk_name)

    # 分隔符
    cb.set_color(ThemeColor.TEXT_MUTED).set_font(faction_font)
    cb.add_text(separator, cursor_x, row2_y + 3)
    cursor_x += sep_w

    # 防守方图标 + 名称
    if def_icon and renderer.font_wf_icon:
        cb.set_color(def_color).set_font(renderer.font_wf_icon)
        cb.add_text(def_icon, cursor_x, row2_y - 2)
        cursor_x += cb.get_string_width(def_icon) + 4
    cb.set_color(def_color).set_font(faction_font)
    cb.add_text(def_name, cursor_x, row2_y + 3)

    # ---- 行 3: 双方奖励 ----
    reward_y = card_y + 134

    # 进攻方奖励
    atk_reward = _get_first_reward_text(invasion.attacker_reward)
    if atk_reward:
        atk_label = f"进攻: {atk_reward}"
        cb.set_color(_ATTACKER_COLOR).set_font(reward_font)
        cb.add_text(atk_label, inner_x, reward_y + 3)

    # 防守方奖励
    def_reward_text = ""
    if invasion.defender_reward and invasion.defender_reward.counted_items:
        item = invasion.defender_reward.counted_items[0]
        def_reward_text = f"{item.count}x {item.name}" if item.count and item.name else ""

    if def_reward_text:
        def_label = f"防守: {def_reward_text}"
        cb.set_color(_DEFENDER_COLOR).set_font(reward_font)
        label_w = cb.get_string_width(def_label)
        cb.add_text(def_label, inner_x + inner_w - label_w, reward_y + 3)


# ---------------------------------------------------------------------------
# 主渲染函数
# ---------------------------------------------------------------------------

def draw_invasion_card(
    renderer: CardRenderer,
    invasions: list[Invasion],
) -> Image.Image:
    """绘制入侵信息卡片 — 单列宽卡片 + 双层边框 + 看板娘 + 底部署名。

    Args:
        renderer: CardRenderer 实例。
        invasions: Invasion 模型列表（已由 Service 翻译并过滤）。

    Returns:
        PIL Image 对象。
    """
    if not invasions:
        return renderer.create_text_image("当前没有活跃的入侵", 800, 120)

    # ---- 排序：按 goal 降序 ----
    sorted_invasions = sorted(invasions, key=lambda inv: inv.goal or 0, reverse=True)

    # ---- 字体 ----
    title_font = FontManager.get_text_font(60)
    node_font = FontManager.get_text_font(36)
    faction_font = FontManager.get_text_font(30)
    reward_font = FontManager.get_text_font(26)
    progress_font = FontManager.get_text_font(28)
    FontManager.get_text_font(22)

    # ---- 布局计算 ----
    n = len(sorted_invasions)
    cards_h = n * _CARD_H + (n - 1) * _ROW_GAP
    content_end = _CONTENT_START_Y + cards_h
    canvas_h = content_end + _STANDING_H + _FOOTER_OFFSET + 20

    # ---- 画布 ----
    cb = ImageCombiner(_CANVAS_W, canvas_h, ThemeColor.BG_DARK)

    # ---- 双层边框 ----
    cb.draw_default_double_border()

    # ---- 标题 ----
    cb.set_color(ThemeColor.DANGER).set_font(title_font)
    cb.add_centered_text("入侵任务", _TITLE_Y)

    # ---- 分割线 ----
    cb.draw_content_divider(_TITLE_Y + 68, _CONTENT_X, _CONTENT_W)

    # ---- 入侵卡片（单列） ----
    for i, invasion in enumerate(sorted_invasions):
        card_y = _CONTENT_START_Y + i * (_CARD_H + _ROW_GAP)
        _draw_one_invasion_card(
            cb, invasion, _CONTENT_X, card_y, renderer,
            node_font, faction_font, reward_font, progress_font,
        )

    # ---- 看板娘（右下角，贴底对齐） ----
    standing_x = _CONTENT_X + _CONTENT_W - _STANDING_W - 20
    standing_y = canvas_h - _STANDING_H - 10
    draw_standing_at(cb, standing_x, standing_y, _STANDING_W, _STANDING_H)

    # ---- 底部署名 ----
    cb.draw_card_footer(canvas_h, _FOOTER_OFFSET, 22)

    return cb.to_image()
