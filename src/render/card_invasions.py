"""入侵卡片渲染器

版式：页头 + 单列宽卡（节点/进度 · 攻守双方 · 进度条 · 双方奖励）+ 看板娘 + 署名。

卡片自上而下四段：

1. 节点（粗体）+ 右侧进度百分比；
2. 进攻方（左，红）对 防守方（右，绿），各有派系图标；
3. 双色进度条：左侧红段 = 进攻进度，右侧绿段 = 防守进度；
4. 进攻奖励（左）/ 防守奖励（右）；全部没有奖励时整行不占位（卡片自动变矮）。

卡片宽由最宽一行决定（夹在 620~1200），高度按四段行高累加。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import card_frame as frame
from . import components as C
from .card_size import CardSpec, CustomBlock, measure_card_size
from .design import FONT, RGB, SPACE, font, semantic_color
from .theme import current_theme

if TYPE_CHECKING:
    from PIL import Image

    from ..model.world_state import Invasion
    from .card_renderer import CardRenderer

#: 卡片内边距。
_CARD_PAD = SPACE["lg"]
#: 进度条高度（决定圆角半径 = 高度的一半）。
_BAR_H = 8
#: 卡片宽下限 / 上限。
_MIN_CARD_W = 620
_MAX_CARD_W = 1200


@dataclass(frozen=True)
class _InvasionRow:
    """一张入侵卡的绘制文案（测宽与绘制共用）。"""

    node: str
    progress: float
    attacker: str
    attacker_color: RGB
    attacker_icon: str
    defender: str
    defender_color: RGB
    defender_icon: str
    attacker_reward: str
    defender_reward: str


def _build_progress(count: float | None, goal: float | None) -> float:
    """进度百分比 (0.0 ~ 1.0)，对齐 Java ``abs(count)/goal``。"""
    if not goal or count is None:
        return 0.0
    return min(abs(count) / goal, 1.0)


def _first_reward_text(rewards: list) -> str:
    """取奖励列表里第一个有数量的物品，格式 ``3x 名称``。"""
    for reward in rewards or []:
        for item in getattr(reward, "counted_items", None) or []:
            name = getattr(item, "name", "") or ""
            count = getattr(item, "count", None)
            if name:
                return f"{count}x {name}" if count else name
    return ""


def _build_row(invasion: Invasion, theme) -> _InvasionRow:
    """把一条 ``Invasion`` 转成绘制文案与颜色。"""
    palette = theme.palette

    attacker = invasion.faction
    attacker_icon = (getattr(attacker, "icon", "") or "") if attacker is not None else ""
    attacker_name = attacker.display_name if attacker is not None else "未知"
    attacker_color = (
        semantic_color(attacker.color, theme, palette.text_muted)
        if attacker is not None
        else palette.text_muted
    )

    defender = invasion.defender_faction
    defender_icon = (getattr(defender, "icon", "") or "") if defender is not None else ""
    defender_name = defender.display_name if defender is not None else "未知"
    defender_color = (
        semantic_color(defender.color, theme, palette.text_muted)
        if defender is not None
        else palette.text_muted
    )

    defender_reward = ""
    if invasion.defender_reward and invasion.defender_reward.counted_items:
        item = invasion.defender_reward.counted_items[0]
        if item.name:
            defender_reward = f"{item.count}x {item.name}" if item.count else item.name

    return _InvasionRow(
        node=invasion.node or "未知节点",
        progress=_build_progress(invasion.count, invasion.goal),
        attacker=attacker_name,
        attacker_color=attacker_color,
        attacker_icon=attacker_icon,
        defender=defender_name,
        defender_color=defender_color,
        defender_icon=defender_icon,
        attacker_reward=_first_reward_text(invasion.attacker_reward),
        defender_reward=defender_reward,
    )


def _group_width(icon: str, name: str, name_font, pad: int) -> int:
    """「图标 + 名称」的总宽（无图标时只剩名称）。"""
    width = C.measure(name, name_font)
    if icon:
        width += pad + FONT["md"]
    return width


def _card_height(has_rewards: bool) -> int:
    """卡片高：上下内边距 + 四段 + 段间距（与 ``_draw_card`` 同口径）。"""
    height = _CARD_PAD * 2 + FONT["md"] * 2 + SPACE["md"] * 2 + _BAR_H
    if has_rewards:
        height += SPACE["md"] + FONT["base"]
    return height


def _row_width(row: _InvasionRow, body_font, reward_font, label_font, value_font) -> int:
    """单张卡最宽的一行（不含内边距）。"""
    progress_w = C.measure("进度", label_font) + SPACE["sm"] + C.measure("100.0%", value_font)
    line1 = C.measure(row.node, font("md", bold=True)) + SPACE["3xl"] + progress_w

    line2 = _group_width(row.attacker_icon, row.attacker, body_font, SPACE["xs"])
    line2 += SPACE["3xl"] * 2 + _group_width(row.defender_icon, row.defender, body_font, SPACE["xs"])

    line4 = 0
    if row.attacker_reward or row.defender_reward:
        line4 = C.measure(f"进攻 {row.attacker_reward}", reward_font)
        line4 += SPACE["3xl"] * 2 + C.measure(f"防守 {row.defender_reward}", reward_font)
    return max(line1, line2, line4)


def _draw_bar(page, x: int, y: int, width: int, progress: float) -> None:
    """双色进度条：左红（进攻）右绿（防守），两端圆角。"""
    palette = page.palette
    cb = page.cb
    radius = _BAR_H // 2
    cb.draw_rounded_rect(
        x, y, width, _BAR_H,
        radius=radius,
        fill=palette.surface_alt,
        outline=palette.border,
        stroke_width=1,
    )

    split = x + round(width * progress)
    # 左侧多画半个圆角，让右段圆角盖住接缝，避免中间出现一条底色缝
    if split - x > radius * 2:
        left_w = min(width, split - x + radius)  # 100% 时不要画到卡片外面
        cb.draw_rounded_rect(x, y, left_w, _BAR_H, radius=radius, fill=palette.red)
    if x + width - split > radius * 2:
        cb.draw_rounded_rect(split, y, x + width - split, _BAR_H, radius=radius, fill=palette.green)


def _draw_card(
    page,
    row: _InvasionRow,
    x: int,
    y: int,
    width: int,
    height: int,
    with_rewards: bool,
) -> None:
    """画一张入侵卡（同行卡片统一高度，没有奖励的那张写「无奖励」，底边对齐）。"""
    palette = page.palette
    cb = page.cb
    C.draw_grid_card(page, x, y, width, height)

    body_font = font("md")
    pad = _CARD_PAD
    inner_w = width - pad * 2

    # ---- 行 1：节点（左）+ 进度（右） ----
    top = y + pad
    cb.set_color(palette.text).set_font(font("md", bold=True))
    label_font = font("sm")
    value_font = font("md", bold=True)
    progress_w = C.measure("进度", label_font) + SPACE["sm"] + C.measure("100.0%", value_font)
    cb.add_text(
        C.fit_text(row.node, inner_w - progress_w - SPACE["xl"], font("md", bold=True)),
        x + pad,
        top,
    )

    pct_text = f"{row.progress * 100:.1f}%"
    pct_x = x + width - pad - C.measure("进度", label_font) - SPACE["sm"] - C.measure(pct_text, value_font)
    cb.set_color(palette.text_dim).set_font(label_font)
    cb.add_text("进度", pct_x, top + FONT["md"] - FONT["sm"])
    cb.set_color(palette.blue).set_font(value_font)
    cb.add_text(pct_text, pct_x + C.measure("进度", label_font) + SPACE["sm"], top)

    # ---- 行 2：进攻方（左） / 防守方（右） ----
    duel_y = top + FONT["md"] + SPACE["md"]
    cursor = x + pad
    if row.attacker_icon:
        cb.set_color(row.attacker_color).set_font(C.icon_font(FONT["md"]))
        cb.add_text(row.attacker_icon, cursor, duel_y)
        cursor += FONT["md"] + SPACE["xs"]
    cb.set_color(row.attacker_color).set_font(body_font)
    cb.add_text(row.attacker, cursor, duel_y)

    defender_w = _group_width(row.defender_icon, row.defender, body_font, SPACE["xs"])
    cursor = x + width - pad - defender_w
    if row.defender_icon:
        cb.set_color(row.defender_color).set_font(C.icon_font(FONT["md"]))
        cb.add_text(row.defender_icon, cursor, duel_y)
        cursor += FONT["md"] + SPACE["xs"]
    cb.set_color(row.defender_color).set_font(body_font)
    cb.add_text(row.defender, cursor, duel_y)

    # ---- 行 3：进度条 ----
    bar_y = duel_y + FONT["md"] + SPACE["md"]
    _draw_bar(page, x + pad, bar_y, inner_w, row.progress)

    # ---- 行 4：双方奖励 ----
    if not with_rewards:
        return
    reward_y = bar_y + _BAR_H + SPACE["md"]
    reward_font = font("base")
    if not (row.attacker_reward or row.defender_reward):
        cb.set_color(palette.text_dim).set_font(reward_font)
        cb.add_text("无奖励", x + pad, reward_y)
        return
    if row.attacker_reward:
        text = f"进攻 {row.attacker_reward}"
        cb.set_color(palette.red).set_font(reward_font)
        cb.add_text(C.fit_text(text, inner_w // 2, reward_font), x + pad, reward_y)
    if row.defender_reward:
        text = f"防守 {row.defender_reward}"
        cb.set_color(palette.green).set_font(reward_font)
        cb.add_text(
            C.fit_text(text, inner_w // 2, reward_font),
            x + width - pad - C.measure(C.fit_text(text, inner_w // 2, reward_font), reward_font),
            reward_y,
        )


def render_invasion_card(
    renderer: CardRenderer,
    invasions: list[Invasion],
) -> Image.Image:
    """绘制入侵信息卡片。

    Args:
        renderer: CardRenderer 实例（保留参数以兼容渲染入口）。
        invasions: Invasion 模型列表（已由 Service 翻译并过滤，按目标值降序排好）。

    Returns:
        PIL Image 对象。
    """
    if not invasions:
        return renderer.create_text_image("当前没有活跃的入侵", 800, 120)

    theme = current_theme()
    rows = [_build_row(invasion, theme) for invasion in sorted(invasions, key=lambda inv: inv.goal or 0, reverse=True)]
    subtitle = f"共 {len(rows)} 个任务"

    # ---- 卡片宽：最宽一行，夹在 [620, 1200] ----
    body_font = font("md")
    reward_font = font("base")
    label_font = font("sm")
    value_font = font("md", bold=True)
    intrinsic = max(_row_width(row, body_font, reward_font, label_font, value_font) for row in rows)
    card_w = max(_MIN_CARD_W, min(_MAX_CARD_W, intrinsic + _CARD_PAD * 2))

    has_rewards = any(row.attacker_reward or row.defender_reward for row in rows)
    card_h = _card_height(has_rewards)
    gap = SPACE["md"]
    cards_h = len(rows) * card_h + (len(rows) - 1) * gap

    size = measure_card_size(
        CardSpec(
            title="入侵任务",
            subtitle=subtitle,
            blocks=[CustomBlock(width=card_w, height=cards_h)],
            standing="md",
        )
    )

    page = C.new_page(theme, size.width, size.height)
    y = C.draw_header(page, "入侵任务", subtitle)

    # 单列卡铺满内容宽（画布有 720 下限，内容宽可能比卡片的自然宽更大）
    drawn_w = max(card_w, page.content_w)
    for index, row in enumerate(rows):
        _draw_card(page, row, page.content_x, y + index * (card_h + gap), drawn_w, card_h, has_rewards)

    frame.draw_standing_block(page, y + cards_h, "md")
    frame.draw_footer_block(page)
    return page.cb.to_image()


# 兼容旧名：命令层与第三方调用仍可用 draw_invasion_card
draw_invasion_card = render_invasion_card
