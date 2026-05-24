"""集团任务卡片渲染器 — 迁移自 Java DefaultDrawSyndicateImage

支持两种渲染模式：
  - Nodes 视图: 简单节点列表（当 sm.nodes 有数据时触发）
  - Jobs 视图: 赏金任务卡片网格（当 sm.jobs 有数据时触发）
    每行 2 张卡片，含任务类型/敌人等级/段位要求/描述/奖励/声望
    卡片边框颜色: 保险库=紫色、无尽=橙色、普通=灰色
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from .draw_constant import DrawConstant, ThemeColor
from .font_manager import FontManager
from .image_combiner import ImageCombiner
from .standing import draw_standing
from .text_utils import wrap_text

if TYPE_CHECKING:
    from ..model.world_state import Job, SyndicateMission
    from .card_renderer import CardRenderer


# ---------------------------------------------------------------------------
# 布局常量
# ---------------------------------------------------------------------------

_CANVAS_W = 1600
_MARGIN = 40
_CONTENT_PAD = 20
_CONTENT_X = _MARGIN + _CONTENT_PAD
_CONTENT_W = _CANVAS_W - 2 * _CONTENT_X

# 卡片网格
_CARDS_PER_ROW = 2
_CARD_W = 550
_CARD_MIN_H = 280
_CARD_MARGIN_X = 40          # 卡片间水平间距
_CARD_MARGIN_Y = 30           # 行间垂直间距
_CARD_RADIUS = 15
_CARD_PAD = 20                # 卡片内边距
_CARD_CONTENT_W = _CARD_W - 2 * _CARD_PAD  # 510

_TITLE_Y = 70
_DIVIDER_Y = 138
_CONTENT_START_Y = 185
_FOOTER_OFFSET = 55

_STANDING_MAX_W = 310
_STANDING_MAX_H = 420

# 卡片边框颜色 — 镜像 Java getJobBorderColor()
_BORDER_PURPLE = (155, 89, 182)     # #9B59B6 保险库
_BORDER_ORANGE = (230, 126, 34)     # #E67E22 无尽
_BORDER_GRAY = (149, 165, 166)      # #95A5A6 普通

# 段位要求颜色
_MR_COLOR = (230, 126, 34)          # #E67E22

# 声望颜色
_XP_COLOR = (39, 174, 96)           # #27AE60

# 卡片背景色
_CARD_BG_COLOR = (22, 33, 62)       # ThemeColor.BG_CARD


# ---------------------------------------------------------------------------
# 主渲染函数
# ---------------------------------------------------------------------------

def render_syndicate_card(
    renderer: CardRenderer,
    sm: SyndicateMission,
) -> Image.Image:
    """绘制集团任务信息卡片 — 镜像 Java DefaultDrawSyndicateImage.drawSyndicateImage()。

    根据数据自动选择 Nodes 视图或 Jobs 视图。

    Args:
        renderer: CardRenderer 实例。
        sm: SyndicateMission 模型。

    Returns:
        PIL Image 对象。
    """
    if sm.nodes:
        return _draw_nodes_view(renderer, sm)
    if sm.jobs:
        return _draw_jobs_view(renderer, sm)

    return renderer.create_text_image("当前没有集团任务数据", 800, 120)


# ---------------------------------------------------------------------------
# Nodes 视图
# ---------------------------------------------------------------------------

def _draw_nodes_view(
    renderer: CardRenderer,
    sm: SyndicateMission,
) -> Image.Image:
    """绘制简单节点列表视图。

    镜像 Java drawNodesView()。
    """
    nodes = sm.nodes
    tag_name = sm.tag.display_name if sm.tag else "集团任务"

    rows = len(nodes)
    content_h = 180 + rows * 50 + _STANDING_MAX_H + _FOOTER_OFFSET
    canvas_h = max(content_h, 400)

    title_font = FontManager.get_text_font(40)
    body_font = FontManager.get_text_font(28)
    footer_font = FontManager.get_text_font(20)

    cb = ImageCombiner(_CANVAS_W, canvas_h, ThemeColor.BG_DARK)

    cb.draw_double_border(
        border_padding=16,
        border_color_outer=ThemeColor.TABLE_BORDER,
        border_color_inner=ThemeColor.DIVIDER,
        stroke=3,
    )

    cb.set_color(ThemeColor.ACCENT_BLUE).set_font(title_font)
    cb.add_centered_text(f"{tag_name} - 节点", _TITLE_Y)

    cb.set_color(ThemeColor.DIVIDER)
    cb.draw_line(_CONTENT_X, _DIVIDER_Y, _CONTENT_X + _CONTENT_W, _DIVIDER_Y, width=1)

    y = 170
    cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(body_font)
    for node in nodes:
        cb.add_centered_text(f"• {node}", y)
        y += 50

    draw_standing(cb, max_w=_STANDING_MAX_W, max_h=_STANDING_MAX_H)

    cb.set_color(ThemeColor.TEXT_MUTED).set_font(footer_font)
    cb.add_centered_text(DrawConstant.FOOTER_TEXT, canvas_h - _FOOTER_OFFSET)

    return cb.to_image()


# ---------------------------------------------------------------------------
# Jobs 视图
# ---------------------------------------------------------------------------

def _draw_jobs_view(
    renderer: CardRenderer,
    sm: SyndicateMission,
) -> Image.Image:
    """绘制赏金任务卡片网格视图。

    镜像 Java drawJobsView()：
      - 第 1 步：计算每个 Job 卡片高度
      - 第 2 步：按每行 2 个卡片计算总高度
      - 第 3 步：依次绘制卡片到主画布
    """
    jobs = sm.jobs
    tag_name = sm.tag.display_name if sm.tag else "集团任务"

    # Step 1: 计算每个卡片高度
    card_heights = [_calc_job_card_height(job) for job in jobs]

    # Step 2: 计算总高度（每行 2 个卡片，取较高者）
    total_rows_height = 0
    for i in range(0, len(card_heights), _CARDS_PER_ROW):
        row_max = card_heights[i]
        if i + 1 < len(card_heights):
            row_max = max(row_max, card_heights[i + 1])
        total_rows_height += row_max + _CARD_MARGIN_Y

    canvas_h = _CONTENT_START_Y + total_rows_height + _STANDING_MAX_H + _FOOTER_OFFSET

    # ---- 字体 ----
    title_font = FontManager.get_text_font(40)
    card_title_font = FontManager.get_text_font(22)
    card_body_font = FontManager.get_text_font(18)
    card_bold_font = FontManager.get_text_font(20)
    footer_font = FontManager.get_text_font(20)

    # ---- 主画布 ----
    cb = ImageCombiner(_CANVAS_W, canvas_h, ThemeColor.BG_DARK)

    cb.draw_double_border(
        border_padding=16,
        border_color_outer=ThemeColor.TABLE_BORDER,
        border_color_inner=ThemeColor.DIVIDER,
        stroke=3,
    )

    # ---- 标题 ----
    cb.set_color(ThemeColor.ACCENT_BLUE).set_font(title_font)
    cb.add_centered_text(f"{tag_name} - 赏金任务", _TITLE_Y)

    cb.set_color(ThemeColor.DIVIDER)
    cb.draw_line(_CONTENT_X, _DIVIDER_Y, _CONTENT_X + _CONTENT_W, _DIVIDER_Y, width=1)

    # ---- 计算列 X 坐标（居中整个卡片网格） ----
    total_grid_w = _CARDS_PER_ROW * _CARD_W + (_CARDS_PER_ROW - 1) * _CARD_MARGIN_X
    grid_start_x = _CONTENT_X + (_CONTENT_W - total_grid_w) // 2

    # Step 3: 绘制卡片
    x = grid_start_x
    y = _CONTENT_START_Y
    card_index = 0

    for i, job in enumerate(jobs):
        # 换行检查
        if card_index > 0 and card_index % _CARDS_PER_ROW == 0:
            x = grid_start_x
            # 上一行最大高度
            prev_max = card_heights[i - 1]
            if i - 2 >= 0:
                prev_max = max(prev_max, card_heights[i - 2])
            y += prev_max + _CARD_MARGIN_Y

        card_img = _draw_job_card(job, card_heights[i], card_title_font, card_body_font, card_bold_font)
        cb.draw_image(card_img, x, y)

        x += _CARD_W + _CARD_MARGIN_X
        card_index += 1

    # ---- 看板娘 ----
    draw_standing(cb, max_w=_STANDING_MAX_W, max_h=_STANDING_MAX_H)

    # ---- 底部署名 ----
    cb.set_color(ThemeColor.TEXT_MUTED).set_font(footer_font)
    cb.add_centered_text(DrawConstant.FOOTER_TEXT, canvas_h - _FOOTER_OFFSET)

    return cb.to_image()


# ---------------------------------------------------------------------------
# Job 卡片绘制
# ---------------------------------------------------------------------------

def _draw_job_card(
    job: Job,
    card_h: int,
    title_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    body_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    bold_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> Image.Image:
    """绘制单张赏金任务卡片 — 镜像 Java drawJobCard()。

    Returns:
        PIL Image 对象。
    """
    border_color = _get_job_border_color(job)

    cb = ImageCombiner(_CARD_W, card_h, ThemeColor.BG_DARK)

    # 卡片背景 + 边框
    cb.set_color(_CARD_BG_COLOR)
    cb.draw_rounded_rect(0, 0, _CARD_W, card_h, radius=_CARD_RADIUS)
    cb.set_color(border_color)
    cb.draw_rounded_rect(0, 0, _CARD_W, card_h, radius=_CARD_RADIUS, outline=border_color, stroke_width=5)

    inner_x = _CARD_PAD
    inner_w = _CARD_W - 2 * _CARD_PAD
    y = 30

    # 1. 任务类型 + 特殊标识
    type_text = job.type or "未知任务"
    if job.is_vault:
        type_text += " [保险库]"
    elif job.endless:
        type_text += " [无尽]"
    cb.set_color(ThemeColor.ACCENT_BLUE).set_font(title_font)
    cb.add_centered_text(type_text, y)
    y += 40

    # 2. 敌人等级
    if job.min_level is not None and job.max_level is not None:
        level_text = f"敌人等级: Lv.{job.min_level} - Lv.{job.max_level}"
        cb.set_color(ThemeColor.TEXT_PRIMARY).set_font(body_font)
        cb.add_text(level_text, inner_x, y)
        y += 30

    # 3. 段位要求（如果存在）
    if job.mastery_req is not None and job.mastery_req > 0:
        mr_text = f"段位要求: MR {job.mastery_req}"
        cb.set_color(_MR_COLOR).set_font(body_font)
        cb.add_text(mr_text, inner_x, y)
        y += 30

    # 4. 任务描述（自动换行）
    if job.desc:
        lines = wrap_text(cb.draw, job.desc, inner_w, body_font)
        cb.set_color(ThemeColor.TEXT_SECONDARY).set_font(body_font)
        for line in lines:
            cb.add_text(line, inner_x, y)
            y += 25
        y += 10

    # 5. 奖励列表
    rewards = _extract_rewards(job)
    if rewards:
        cb.set_color(ThemeColor.ACCENT_GOLD).set_font(bold_font)
        cb.add_text("奖励:", inner_x, y)
        y += 30

        for reward_item, reward_count, rarity in rewards:
            rarity_color = _get_rarity_color(rarity)
            reward_text = f"  • {reward_item} x{reward_count}"
            cb.set_color(rarity_color).set_font(body_font)
            cb.add_text(reward_text, inner_x, y)
            y += 25

    # 6. 声望奖励（底部固定位置）
    if job.xp_amounts:
        total_xp = sum(job.xp_amounts)
        cb.set_color(_XP_COLOR).set_font(bold_font)
        cb.add_text(f"声望奖励: {total_xp}", inner_x, card_h - 30)

    return cb.to_image()


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _calc_job_card_height(job: Job) -> int:
    """计算单个 Job 卡片所需高度 — 镜像 Java calculateJobCardHeight()。"""
    h = 30   # 顶部内边距
    h += 40  # 任务类型
    h += 30  # 敌人等级

    # 段位要求
    if job.mastery_req is not None and job.mastery_req > 0:
        h += 30

    # 任务描述（动态行数）
    if job.desc:
        # 用临时 draw + 18px 字体估算行数
        temp_img = Image.new("RGBA", (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)
        body_font = FontManager.get_text_font(18)
        lines = wrap_text(temp_draw, job.desc, _CARD_CONTENT_W, body_font)
        h += len(lines) * 25 + 10

    # 奖励标题
    rewards = _extract_rewards(job)
    if rewards:
        h += 30  # "奖励:" 标题
        h += len(rewards) * 25

    # 声望
    h += 40

    # 内边距
    h += 30

    return max(h, _CARD_MIN_H)


def _extract_rewards(job: Job) -> list[tuple[str, int, str]]:
    """从 Job.reward_pool 提取奖励列表。

    reward_pool 是 dict，格式: {"rewards": [{"item": "...", "itemCount": N, "rarity": "RARE"}, ...]}

    Returns:
        [(item_name, item_count, rarity_string), ...] 列表。
    """
    if not job.reward_pool or not isinstance(job.reward_pool, dict):
        return []

    rewards_data = job.reward_pool.get("rewards")
    if not rewards_data or not isinstance(rewards_data, list):
        return []

    result: list[tuple[str, int, str]] = []
    for r in rewards_data:
        if not isinstance(r, dict):
            continue
        name = str(r.get("item", r.get("ItemType", "未知物品")))
        count = r.get("itemCount", r.get("ItemCount", 1))
        rarity = str(r.get("rarity", r.get("Rarity", "COMMON")))
        try:
            count = int(count)
        except (TypeError, ValueError):
            count = 1
        result.append((name, count, rarity))

    return result


def _get_job_border_color(job: Job) -> tuple[int, int, int]:
    """根据任务类型获取卡片边框颜色 — 镜像 Java getJobBorderColor()。"""
    if job.is_vault:
        return _BORDER_PURPLE
    if job.endless:
        return _BORDER_ORANGE
    return _BORDER_GRAY


def _get_rarity_color(rarity: str) -> tuple[int, int, int]:
    """根据稀有度字符串获取颜色 — 镜像 Java getRarityColor()。"""
    rarity_upper = rarity.upper().strip()
    if rarity_upper == "COMMON":
        return ThemeColor.VOID_T2    # #75562B
    if rarity_upper == "UNCOMMON":
        return ThemeColor.VOID_T3    # #9F9E9E
    if rarity_upper == "RARE":
        return ThemeColor.VOID_T4    # #C1BE39
    if rarity_upper == "LEGENDARY":
        return ThemeColor.VOID_T5    # #872A2C
    return ThemeColor.TEXT_PRIMARY
