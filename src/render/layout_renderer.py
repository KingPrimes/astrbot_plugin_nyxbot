"""Layout renderer / 版式渲染器（样板）

把「版式」从代码搬到 JSON：一张卡 = 有序的 block 列表，每个 block 有 ``type``
和 ``props``。本模块实现遗物卡需要的五种块（header / chips / grid /
standing / footer），作为后续工作台（拖拽自定义）的解释器雏形。

设计约束
--------
1. **只认白名单**：``type`` 必须是 :data:`BLOCK_TYPES` 之一，未知块忽略；
2. **参数收敛**：列数、条数、看板娘尺寸等全部 clamp 到安全区间，
   防止用户填出 10 万像素的画布；
3. **版式与数据分离**：渲染函数只接收「已摊平的数据 + 版式」，不碰 ORM；
4. **块用 enabled 开关**：删除块与关闭块是两回事 —— 关闭保留块和顺序，
   避免「重新加载后又冒出来」；旧版式（v1，靠删块关闭）在迁移时补成
   ``enabled: false``，观感不变。

版式示例::

    {
      "version": 2,
      "card": "relics",
      "blocks": [
        {"type": "header",   "props": {"title": "遗物查询"}},
        {"type": "chips",    "props": {}},
        {"type": "grid",     "props": {"columns": 3, "maxItems": 20, "rewardsPerCard": 6}},
        {"type": "standing", "props": {"enabled": true, "seasonal": true, "size": "md"}},
        {"type": "footer",   "props": {"text": "Posted by: KingPrimes"}}
      ]
    }
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from PIL import Image

from . import components as C
from . import standing as standing_mod
from .branding import STANDING_SIZES, signature_text
from .design import FONT, PAD, SPACE, Theme, font, resolve_width
from .theme import current_theme

#: 允许的块类型（顺序即默认版式顺序）。
BLOCK_TYPES: tuple[str, ...] = ("header", "chips", "grid", "standing", "footer")

#: 版式版本：2 起用 ``enabled`` 控制块开关（1 靠删块）。
LAYOUT_VERSION = 2

#: 默认版式。
DEFAULT_LAYOUT: dict[str, Any] = {
    "version": LAYOUT_VERSION,
    "card": "relics",
    "blocks": [
        {
            "type": "header",
            "props": {
                "enabled": True,
                "title": "遗物查询",
                "subtitle": "{count} 个遗物 · {rewards} 条奖励",
            },
        },
        {"type": "chips", "props": {"enabled": True}},
        {
            "type": "grid",
            "props": {
                "enabled": True,
                "columns": 3,
                "maxItems": 20,
                "rewardsPerCard": 6,
                "rewardLines": 1,
                "showDucats": True,
            },
        },
        {
            "type": "standing",
            "props": {"enabled": True, "seasonal": True, "size": "md"},
        },
        # text 留空 = 用品牌设置里的全局署名（工作台「全局默认」可改）
        {"type": "footer", "props": {"enabled": True, "text": ""}},
    ],
}

#: 各 props 的安全区间。
_LIMITS: dict[str, tuple[int, int]] = {
    "columns": (2, 4),
    "maxItems": (1, 40),
    "rewardsPerCard": (1, 6),
    "rewardLines": (1, 2),
}

#: 署名最大字符数（防止把画布撑爆）。
_SIGNATURE_MAX_LEN = 120

#: 稀有度 → 调色板字段。
_RARITY_FIELD = {
    "COMMON": "rarity_common",
    "UNCOMMON": "rarity_uncommon",
    "RARE": "rarity_rare",
    "LEGENDARY": "rarity_legendary",
}


def _clamp(value: Any, key: str, fallback: int) -> int:
    low, high = _LIMITS[key]
    try:
        number = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(low, min(high, number))


def _as_bool(value: Any, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes", "on", "是", "开"}:
            return True
        if text in {"0", "false", "no", "off", "否", "关"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return fallback


def _normalize_props(block_type: str, props: dict[str, Any]) -> dict[str, Any]:
    """按块类型收敛 props。"""
    props["enabled"] = _as_bool(props.get("enabled"), True)

    if block_type == "grid":
        props["columns"] = _clamp(props.get("columns"), "columns", 3)
        props["maxItems"] = _clamp(props.get("maxItems"), "maxItems", 20)
        props["rewardsPerCard"] = _clamp(props.get("rewardsPerCard"), "rewardsPerCard", 6)
        # 1 = 单行截断；2 = 换行两行（仍放不下才省略）
        props["rewardLines"] = _clamp(props.get("rewardLines"), "rewardLines", 1)
        props["showDucats"] = _as_bool(props.get("showDucats"), True)
    elif block_type == "standing":
        props["seasonal"] = _as_bool(props.get("seasonal"), True)
        size = str(props.get("size", "")).strip().lower()
        props["size"] = size if size in STANDING_SIZES else "md"
    elif block_type == "footer":
        text = props.get("text")
        text = "" if text is None else str(text).strip()[:_SIGNATURE_MAX_LEN]
        props["text"] = text
    elif block_type == "header":
        for key in ("title", "subtitle"):
            value = props.get(key)
            props[key] = "" if value is None else str(value)[:120]

    return props


def _merge_blocks(payload: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """把用户版式合并到默认块骨架上。

    缺失的块会被补回并标成 ``enabled: false``（旧版式里删块 = 关闭），
    唯独 ``standing`` 是新块，缺失时默认开启 —— 否则老版式永远看不到看板娘。
    """
    raw_blocks: Any = payload.get("blocks") if isinstance(payload, Mapping) else None

    incoming: dict[str, Mapping[str, Any]] = {}
    if isinstance(raw_blocks, list):
        for raw in raw_blocks:
            if not isinstance(raw, Mapping):
                continue
            block_type = str(raw.get("type", "")).strip()
            if block_type in BLOCK_TYPES and block_type not in incoming:
                incoming[block_type] = raw

    merged: list[dict[str, Any]] = []
    for default in DEFAULT_LAYOUT["blocks"]:
        block_type = default["type"]
        props = dict(default["props"])
        raw = incoming.get(block_type)

        if raw is None:
            # 旧版式删掉的块视为关闭；standing 是新增块，缺失时给一次默认开启
            props["enabled"] = block_type == "standing"
            merged.append({"type": block_type, "props": _normalize_props(block_type, props)})
            continue

        raw_props = raw.get("props")
        if isinstance(raw_props, Mapping):
            for key, value in raw_props.items():
                if key in props:
                    props[key] = value
        merged.append({"type": block_type, "props": _normalize_props(block_type, props)})

    return merged


def normalize_layout(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """把任意输入收敛成合法版式：补默认块、夹参数、丢未知块。"""
    return {
        "version": LAYOUT_VERSION,
        "card": "relics",
        "blocks": _merge_blocks(payload),
    }


def _rarity_color(rarity: str | None, theme: Theme) -> tuple[int, int, int]:
    field = _RARITY_FIELD.get((rarity or "").upper())
    return getattr(theme.palette, field) if field else theme.palette.text_muted


def _count_rewards(relics: Iterable[Mapping[str, Any]]) -> int:
    return sum(len(relic.get("rewards") or []) for relic in relics)


def _standing_target(
    props: Mapping[str, Any],
    content_w: int,
) -> tuple[Image.Image | None, int, int]:
    """解析看板娘：返回 (图片, 宽, 高)；禁用或素材缺失时宽高为 0。"""
    if not props.get("enabled", True):
        return None, 0, 0

    max_w, max_h = STANDING_SIZES.get(str(props.get("size", "md")), STANDING_SIZES["md"])
    image = standing_mod.pick_standing_image(
        seasonal=_as_bool(props.get("seasonal"), True),
        enabled=True,
    )
    if image is None:
        return None, 0, 0

    target_w, target_h = standing_mod.resize_fit(image, min(max_w, content_w), max_h)
    return image, target_w, target_h


def render_relic_layout(
    relics: list[Mapping[str, Any]],
    layout: Mapping[str, Any] | None = None,
    theme: Theme | None = None,
) -> Image.Image:
    """按版式渲染遗物卡。

    Args:
        relics: 已摊平的遗物数据，字段见 ``web_api.relic_studio._load_relics``。
        layout: 版式（会先过 :func:`normalize_layout`）。
        theme: 主题；默认取当前主题。

    Returns:
        PIL Image。
    """
    theme = theme or current_theme()
    palette = theme.palette
    layout = normalize_layout(layout)
    order = [block["type"] for block in layout["blocks"]]
    blocks = {block["type"]: block["props"] for block in layout["blocks"]}

    def enabled(name: str) -> bool:
        return bool(blocks.get(name, {}).get("enabled", True))

    grid = blocks.get("grid", {})
    columns = grid.get("columns", 3)
    max_items = grid.get("maxItems", 20)
    rewards_per_card = grid.get("rewardsPerCard", 6)
    reward_lines = grid.get("rewardLines", 1)
    show_ducats = grid.get("showDucats", True)

    shown = relics[:max_items]
    reward_total = _count_rewards(shown)
    rare_total = sum(
        1
        for relic in shown
        for reward in (relic.get("rewards") or [])
        if (reward.get("rarity") or "").upper() == "RARE"
    )

    # ---- 测量 ----
    card_gap = SPACE["lg"]
    line_h = FONT["sm"] + SPACE["xs"]
    card_pad = SPACE["lg"]

    header = blocks.get("header", {})
    title = str(header.get("title", "遗物查询"))
    subtitle_tpl = str(header.get("subtitle", ""))
    subtitle = (
        subtitle_tpl.format(count=len(shown), rewards=reward_total)
        if subtitle_tpl and "{" in subtitle_tpl
        else subtitle_tpl
    )

    intrinsic = max(
        C.measure_header(title, subtitle) if enabled("header") else 0,
        len(grid) * 120,
        760,
    )
    width = resolve_width(intrinsic)
    content_w = width - PAD * 2

    if columns > 1:
        card_w = (content_w - card_gap * (columns - 1)) // columns
    else:
        card_w = content_w

    # 先把每张卡的奖励行排好（受 rewardLines 影响），再按「最高的那张卡」定 card_h：
    # 网格必须等高，但不能用「每条都 2 行」的最坏情况把矮卡拉高。
    name_font = font("md", bold=True)
    reward_font = font("sm")
    reward_indent = C.measure("· ", reward_font) if reward_lines > 1 else 0
    # 两行模式：行距与条目间距都放宽一点，否则续行和下一张条目糊在一起
    reward_line_h = line_h + 2 if reward_lines > 1 else line_h
    reward_gap = SPACE["xs"] if reward_lines > 1 else 0
    prepared: list[tuple[str, list[tuple[list[str], tuple[int, int, int], str | None]]]] = []
    for relic in shown:
        name = str(relic.get("name") or "未知遗物")
        rows_data: list[tuple[list[str], tuple[int, int, int], str | None]] = []
        for reward in (relic.get("rewards") or [])[:rewards_per_card]:
            reward_name = str(reward.get("name") or "?")
            reserve = 34 if show_ducats else 0
            lines = C.wrap_lines(
                f"· {reward_name}",
                card_w - card_pad * 2 - reserve,
                reward_font,
                max_lines=reward_lines,
                indent=reward_indent,
            )
            ducats = f"{reward['ducats']}" if (show_ducats and reward.get("ducats")) else None
            rows_data.append((lines, _rarity_color(reward.get("rarity"), theme), ducats))
        prepared.append((name, rows_data))

    def _body_height(rows_data: list[tuple[list[str], tuple[int, int, int], str | None]]) -> int:
        return sum(len(lines) * reward_line_h + reward_gap for lines, _, _ in rows_data)

    card_h = card_pad * 2 + FONT["md"] + SPACE["sm"] + max(
        (_body_height(rows_data) for _, rows_data in prepared),
        default=line_h,
    )
    rows = (len(shown) + columns - 1) // columns if shown else 0
    grid_h = rows * card_h + max(0, rows - 1) * card_gap

    chips: list[tuple[str, str]] = []
    if enabled("chips"):
        chips = [
            ("遗物", str(len(shown))),
            ("奖励", str(reward_total)),
            ("稀有", str(rare_total)),
        ]

    _, standing_w, standing_h = _standing_target(blocks.get("standing", {}), content_w)
    # 版式里的 text 为空 → 回落到全局署名
    footer_text = str(blocks.get("footer", {}).get("text") or "").strip() or signature_text()

    header_h = (FONT["2xl"] + SPACE["xl"] + SPACE["xl"]) if enabled("header") else 0
    chips_h = (FONT["md"] + SPACE["md"]) if chips else 0
    standing_block_h = (standing_h + SPACE["xl"]) if standing_h else 0
    footer_h = (FONT["sm"] + SPACE["md"]) if (enabled("footer") and footer_text) else 0

    height = (
        C.content_top()
        + header_h
        + chips_h
        + grid_h
        + standing_block_h
        + SPACE["xl"]
        + footer_h
        + C.footer_space()
    )

    # ---- 绘制 ----
    page = C.new_page(theme, width, height)
    cb = page.cb
    y = C.content_top()

    for block_type in order:
        if block_type == "header":
            if enabled("header"):
                y = C.draw_header(page, title, subtitle)
            else:
                y += header_h
        elif block_type == "chips":
            if chips:
                y = C.draw_chips(page, chips, y) + SPACE["md"]
            else:
                y += chips_h
        elif block_type == "grid":
            start_y = y
            for index, (name, rows_data) in enumerate(prepared):
                row, column = divmod(index, columns)
                x = page.content_x + column * (card_w + card_gap)
                top = start_y + row * (card_h + card_gap)
                C.draw_grid_card(page, x, top, card_w, card_h, index=index + 1)

                cb.set_color(palette.text).set_font(name_font)
                cb.add_text(
                    C.fit_text(name, card_w - card_pad * 2, name_font),
                    x + card_pad,
                    top + card_pad,
                )

                line_y = top + card_pad + FONT["md"] + SPACE["sm"]
                for lines, color, ducats in rows_data:
                    cb.set_color(color).set_font(reward_font)
                    for offset, text_line in enumerate(lines):
                        # 续行缩进到正文起点，避免看起来像新条目
                        shift = reward_indent if offset else 0
                        cb.add_text(
                            text_line, x + card_pad + shift, line_y + offset * reward_line_h
                        )

                    if ducats:
                        cb.set_color(palette.text_dim).set_font(font("xs"))
                        cb.add_text(
                            ducats,
                            x + card_w - card_pad - C.measure(ducats, font("xs")),
                            line_y + 2,
                        )
                    line_y += len(lines) * reward_line_h + reward_gap
            y = start_y + grid_h
        elif block_type == "standing":
            if standing_h:
                # 右对齐；与网格之间留一段呼吸，避免贴着最后一排卡片
                top = y + SPACE["xl"]
                standing_mod.draw_standing_at(
                    cb,
                    page.content_x + content_w - standing_w,
                    top,
                    standing_w,
                    standing_h,
                    seasonal=_as_bool(blocks.get("standing", {}).get("seasonal"), True),
                    enabled=True,
                )
            y += standing_block_h
        elif block_type == "footer":
            if enabled("footer") and footer_text:
                C.draw_footer(page, footer_text)
            y += footer_h

    return page.cb.to_image()
