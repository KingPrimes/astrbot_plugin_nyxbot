"""集团任务卡片渲染器

集团只有「赏金任务」一个用途，所以只有一种版式：
页头（``{集团} · 赏金``）+ 两列赏金卡网格 + 看板娘 + 署名。

赏金卡自上而下：任务类型（+ 保险库/无尽标记，右上角声望）+ 敌人等级 / 段位要求
+ 描述（最多 3 行）+ 奖励清单（按稀有度着色）。卡片边框按类型着色
（保险库紫 / 无尽橙 / 普通灰），宽高全部按内容量出来，不再写死 1600×N。

数据侧 ``WorldStateService.get_syndicate_mission()`` 只返回 ``jobs`` 非空的条目，
``Nodes`` 字段（旧版 Java 的节点清单视图）不再参与渲染。
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from . import card_frame as frame
from . import components as C
from .card_size import CardSpec, CustomBlock, measure_card_size
from .design import FONT, RADIUS, RGB, SPACE, font, semantic_color
from .theme import current_theme

if TYPE_CHECKING:
    from PIL import Image

    from ..model.world_state import Job, SyndicateMission
    from .card_renderer import CardRenderer

#: 卡片内边距。
_CARD_PAD = SPACE["lg"]
#: 赏金卡每行列数。
_COLUMNS = 2
#: 赏金卡宽下限 / 上限。
_MIN_CARD_W = 420
_MAX_CARD_W = 640
#: 描述最多几行（超出截断），避免个别长描述把整行卡片拉高。
_DESC_LINES = 3
#: 奖励最多几条（超出折成「另 n 项」）。
_MAX_REWARDS = 6

#: 卡片边框色：保险库紫 / 无尽橙 / 普通灰。
_BORDER_COLORS: dict[str, str] = {
    "vault": "#9B59B6",
    "endless": "#E67E22",
    "normal": "#95A5A6",
}


@dataclass(frozen=True)
class _JobRow:
    """一张赏金卡的绘制文案。"""

    title: str
    tag: str
    tag_color: RGB
    border: RGB
    level: str
    mastery: str
    desc: list[str]
    rewards: list[tuple[str, RGB]]
    xp: str
    height: int


# ---------------------------------------------------------------------------
# 数据整理
# ---------------------------------------------------------------------------


def _tag_name(sm: SyndicateMission) -> str:
    return sm.tag.display_name if sm.tag is not None else "集团任务"


def _extract_rewards(job: Job) -> list[tuple[str, str]]:
    """从 ``job.reward_pool`` 提取 ``(名称, 稀有度)`` 列表。"""
    pool = job.reward_pool
    if not pool or not isinstance(pool, dict):
        return []
    rewards_data = pool.get("rewards")
    if not rewards_data or not isinstance(rewards_data, list):
        return []

    result: list[tuple[str, str]] = []
    for entry in rewards_data:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("item", entry.get("ItemType", "未知物品")))
        rarity = str(entry.get("rarity", entry.get("Rarity", "COMMON")))
        result.append((name, rarity))
    return result


def _rarity_color(rarity: str, palette) -> RGB:
    """稀有度 → 主题色板（未知名按常见处理）。"""
    key = (rarity or "").strip().upper()
    return {
        "COMMON": palette.rarity_common,
        "UNCOMMON": palette.rarity_uncommon,
        "RARE": palette.rarity_rare,
        "LEGENDARY": palette.rarity_legendary,
    }.get(key, palette.text)


def _job_border(job: Job, theme) -> RGB:
    palette = theme.palette
    if job.is_vault:
        return semantic_color(_BORDER_COLORS["vault"], theme, palette.border)
    if job.endless:
        return semantic_color(_BORDER_COLORS["endless"], theme, palette.border)
    return semantic_color(_BORDER_COLORS["normal"], theme, palette.border)


def _level_text(job: Job) -> str:
    """敌人等级区间文案；缺数据时为空串。"""
    if job.min_level is not None and job.max_level is not None:
        return f"Lv.{job.min_level} - {job.max_level}"
    if job.min_level is not None:
        return f"Lv.{job.min_level}+"
    return ""


def _mastery_text(job: Job) -> str:
    """段位要求文案；无要求时为空串。"""
    return f"MR {job.mastery_req}" if job.mastery_req else ""


def _job_parts(job: Job, card_w: int, theme) -> _JobRow:
    """把一条 ``Job`` 转成绘制文案（描述按卡宽换行）。"""
    palette = theme.palette
    inner_w = card_w - _CARD_PAD * 2

    if job.is_vault:
        tag, tag_color = "保险库", semantic_color(_BORDER_COLORS["vault"], theme, palette.text_muted)
    elif job.endless:
        tag, tag_color = "无尽", semantic_color(_BORDER_COLORS["endless"], theme, palette.text_muted)
    else:
        tag, tag_color = "", palette.text_muted

    desc: list[str] = []
    if job.desc:
        desc = C.wrap_lines(job.desc, inner_w, font("sm"), max_lines=_DESC_LINES)

    rewards = [
        (name, _rarity_color(rarity, palette)) for name, rarity in _extract_rewards(job)
    ]
    if len(rewards) > _MAX_REWARDS:
        # 超出部分折成一行提示，保持卡片高度可控
        hidden = len(rewards) - _MAX_REWARDS
        rewards = rewards[:_MAX_REWARDS] + [(f"另 {hidden} 项", palette.text_dim)]

    xp = f"声望 {sum(job.xp_amounts):,}" if job.xp_amounts else ""

    row = _JobRow(
        title=job.type or "未知任务",
        tag=tag,
        tag_color=tag_color,
        border=_job_border(job, theme),
        level=_level_text(job),
        mastery=_mastery_text(job),
        desc=desc,
        rewards=rewards,
        xp=xp,
        height=0,
    )
    return _with_height(row)


def _with_height(row: _JobRow) -> _JobRow:
    """按绘制顺序累加卡片高度（与 ``_draw_job_card`` 同口径）。"""
    height = _CARD_PAD
    height += FONT["md"] + SPACE["md"]          # 任务类型 + 声望
    height += FONT["sm"] + SPACE["sm"]          # 等级 / 段位
    if row.desc:
        height += len(row.desc) * (FONT["sm"] + SPACE["xs"]) + SPACE["sm"]
    if row.rewards:
        height += FONT["sm"] + SPACE["xs"]      # 「奖励」标签
        height += len(row.rewards) * (FONT["sm"] + SPACE["xs"])
    return replace(row, height=height + _CARD_PAD)


def _job_width(job: Job, theme) -> int:
    """单张赏金卡的自然宽度（不含内边距）。"""
    title_font = font("md", bold=True)
    small_font = font("sm")

    width = C.measure(job.type or "未知任务", title_font)
    if job.is_vault:
        width += SPACE["md"] + C.measure("保险库", small_font)
    elif job.endless:
        width += SPACE["md"] + C.measure("无尽", small_font)
    if job.xp_amounts:
        width += SPACE["3xl"] + C.measure(f"声望 {sum(job.xp_amounts):,}", title_font)

    level, mastery = _level_text(job), _mastery_text(job)
    meta_w = C.measure(level, small_font) + C.measure(mastery, small_font)
    if level and mastery:
        meta_w += SPACE["xl"]
    width = max(width, meta_w)

    for name, _rarity in _extract_rewards(job)[: _MAX_REWARDS + 1]:
        width = max(width, C.measure(f"• {name}", small_font) + SPACE["sm"])

    # 描述至少给 220px 换行宽，太窄会把一行字拆成三行
    return max(width, 220)


# ---------------------------------------------------------------------------
# 绘制
# ---------------------------------------------------------------------------


def _draw_job_card(page, row: _JobRow, x: int, y: int, width: int, height: int) -> None:
    """画一张赏金卡（同行统一高度，矮的那张底部留白）。"""
    palette = page.palette
    cb = page.cb
    cb.draw_rounded_rect(
        x, y, width, height,
        radius=RADIUS["md"],
        fill=palette.surface_alt,
        outline=row.border,
        stroke_width=2,
    )

    inner_w = width - _CARD_PAD * 2
    cursor_x = x + _CARD_PAD
    top = y + _CARD_PAD

    # ---- 任务类型 + 类型标记（左）+ 声望（右） ----
    title_font = font("md", bold=True)
    small_font = font("sm")
    xp_w = C.measure(row.xp, title_font) + SPACE["xl"] if row.xp else 0
    tag_w = C.measure(row.tag, small_font) + SPACE["md"] if row.tag else 0

    if row.xp:
        cb.set_color(palette.green).set_font(title_font)
        cb.add_text(row.xp, x + width - _CARD_PAD - C.measure(row.xp, title_font), top)

    title = C.fit_text(row.title, inner_w - xp_w - tag_w, title_font)
    cb.set_color(palette.blue).set_font(title_font)
    cb.add_text(title, cursor_x, top)

    if row.tag:
        cb.set_color(row.tag_color).set_font(small_font)
        cb.add_text(row.tag, cursor_x + C.measure(title, title_font) + SPACE["md"], top + 6)

    # ---- 敌人等级 + 段位要求 ----
    meta_y = top + FONT["md"] + SPACE["md"]
    cursor = cursor_x
    if row.level:
        cb.set_color(palette.text_muted).set_font(small_font)
        cb.add_text(f"敌人等级 {row.level}", cursor, meta_y)
        cursor += C.measure(f"敌人等级 {row.level}", small_font) + SPACE["xl"]
    if row.mastery:
        cb.set_color(palette.amber).set_font(small_font)
        cb.add_text(row.mastery, cursor, meta_y)

    # ---- 描述 ----
    cursor_y = meta_y + FONT["sm"] + SPACE["sm"]
    if row.desc:
        cb.set_color(palette.text_muted).set_font(small_font)
        for line in row.desc:
            cb.add_text(line, cursor_x, cursor_y)
            cursor_y += FONT["sm"] + SPACE["xs"]
        cursor_y += SPACE["sm"]

    # ---- 奖励 ----
    if row.rewards:
        cb.set_color(palette.gold).set_font(small_font)
        cb.add_text("奖励", cursor_x, cursor_y)
        cursor_y += FONT["sm"] + SPACE["xs"]

        bullet_w = C.measure("• ", small_font)
        for name, color in row.rewards:
            cb.set_color(color).set_font(small_font)
            cb.add_text("•", cursor_x, cursor_y)
            cb.add_text(
                C.fit_text(name, inner_w - bullet_w, small_font),
                cursor_x + bullet_w,
                cursor_y,
            )
            cursor_y += FONT["sm"] + SPACE["xs"]


def render_syndicate_card(
    renderer: CardRenderer,
    sm: SyndicateMission,
) -> Image.Image:
    """绘制集团赏金卡片：页头 + 两列赏金卡 + 看板娘 + 署名。

    Args:
        renderer: CardRenderer 实例（空数据时用它出提示图）。
        sm: SyndicateMission 模型（``jobs`` 已由 Service 翻译）。

    Returns:
        PIL Image 对象。
    """
    theme = current_theme()
    jobs = sm.jobs
    if not jobs:
        return renderer.create_text_image("当前没有集团任务数据", 800, 120)

    title = f"{_tag_name(sm)} · 赏金"
    subtitle = f"共 {len(jobs)} 个任务"

    # ---- 卡片宽：各卡自然宽取大，夹在 [420, 640] ----
    intrinsic = max(_job_width(job, theme) for job in jobs)
    card_w = max(_MIN_CARD_W, min(_MAX_CARD_W, intrinsic + _CARD_PAD * 2))

    rows = [_job_parts(job, card_w, theme) for job in jobs]
    gap = SPACE["lg"]

    # 每行取较高的一张，两列等高（否则下一行会错位）
    row_heights = [
        max(rows[index].height, rows[index + 1].height if index + 1 < len(rows) else 0)
        for index in range(0, len(rows), _COLUMNS)
    ]
    grid_w = card_w * _COLUMNS + gap
    grid_h = sum(row_heights) + max(0, len(row_heights) - 1) * gap

    size = measure_card_size(
        CardSpec(
            title=title,
            subtitle=subtitle,
            blocks=[CustomBlock(width=grid_w, height=grid_h)],
            standing="md",
        )
    )

    page = C.new_page(theme, size.width, size.height)
    y = C.draw_header(page, title, subtitle)

    grid_x = page.content_x + max(0, (page.content_w - grid_w) // 2)
    offset_y = 0
    for row_index, row_height in enumerate(row_heights):
        for column in range(_COLUMNS):
            index = row_index * _COLUMNS + column
            if index >= len(rows):
                break
            _draw_job_card(
                page,
                rows[index],
                grid_x + column * (card_w + gap),
                y + offset_y,
                card_w,
                row_height,
            )
        offset_y += row_height + gap

    frame.draw_standing_block(page, y + grid_h, "md")
    frame.draw_footer_block(page)
    return page.cb.to_image()
