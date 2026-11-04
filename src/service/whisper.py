"""Whisper service / 私聊语句生成

把订单/拍卖转成可以直接粘进游戏聊天的 ``/w 玩家名 ...``。文案依据 2026-11-04 网页实测：

```
/w Buyer02 Hi! I want to buy: x6 "Primary Deadhead (rank 0)" for 6 platinum. (warframe.market)
/w Buyer01 你好! 我想以20白金购买: "主要·死首 (等级 5)"。(warframe.market)
```

- **订单**：完全照抄官网格式（含 `(warframe.market)` 后缀）；
- **紫卡**：官网只给 `你好!`，我们补上武器名与紫卡名，到名字为止（不带词条/价格）；
- **玄骸**：补武器名与元素加成；
- **语言**：跟随该条卖家 ``locale``（`zh-hans`/`zh-hant` → 中文，其余 → 英文），
  缺失时兜底英文（warframe.market 以英文为通用语）。

设计见 ``plans/market_whisper_design_2026-11-04.md``。
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from astrbot.api import logger

from ..model.market.whisper import WhisperEntry

PICK_TTL = 120.0
"""候选记忆有效期（秒）。比物品名候选的 60 秒稍长，够看清卡片。"""

_ZH_LOCALES = frozenset({"zh", "zh-hans", "zh-hant", "zh-cn", "zh-tw"})

_ELEMENT_NAMES: dict[str, tuple[str, str]] = {
    "impact": ("冲击", "Impact"),
    "heat": ("火焰", "Heat"),
    "cold": ("冰冻", "Cold"),
    "electricity": ("电击", "Electricity"),
    "toxin": ("毒素", "Toxin"),
    "magnetic": ("磁力", "Magnetic"),
    "radiation": ("辐射", "Radiation"),
}

_MARKET_SUFFIX = " (warframe.market)"


def pick_lang(locale: str | None, fallback: str = "en") -> str:
    """按卖家 locale 选模板语言。"""
    if not locale:
        return fallback
    return "zh" if str(locale).lower() in _ZH_LOCALES else "en"


def _element_name(element: str | None, lang: str) -> str:
    if not element:
        return ""
    zh, en = _ELEMENT_NAMES.get(element.lower(), (element, element.title()))
    return zh if lang == "zh" else en


def _order_type(value: object) -> str:
    """``TransactionEnum`` / str 统一成 "buy" / "sell"。"""
    return str(getattr(value, "value", value) or "")


def order_whisper(
    order,
    name_zh: str | None,
    name_en: str | None,
    fallback: str = "en",
) -> WhisperEntry | None:
    """订单 → 私聊语句。

    Args:
        order: ``OrderWithUser``。
        name_zh: 中文物品名（``ordersitems.name``）。
        name_en: 英文物品名（``ordersitems.enName``）。
        fallback: 卖家 locale 缺失时的语言。

    Returns:
        ``WhisperEntry``；没有玩家名时返回 ``None``。
    """
    user = getattr(order, "user", None)
    ingame_name = getattr(user, "ingame_name", None) if user else None
    if not ingame_name:
        return None

    locale = getattr(user, "locale", None) or ""
    lang = pick_lang(locale, fallback)
    name = (name_en if lang == "en" else name_zh) or name_zh or name_en or ""

    price = getattr(order, "platinum", None)
    quantity = getattr(order, "quantity", None) or 1
    rank = getattr(order, "rank", None)
    qty_prefix = f"x{quantity} " if quantity > 1 else ""

    # 订单 type=sell（他在卖）→ 我去买；type=buy（他在收）→ 我去卖
    i_buy = _order_type(getattr(order, "type", "")) == "sell"

    if lang == "zh":
        verb = "购买" if i_buy else "出售"
        rank_part = f" (等级 {rank})" if rank is not None else ""
        text = (
            f'/w {ingame_name} 你好! 我想以{price}白金{verb}: '
            f'{qty_prefix}"{name}{rank_part}"。{_MARKET_SUFFIX.strip()}'
        )
    else:
        verb = "buy" if i_buy else "sell"
        rank_part = f" (rank {rank})" if rank is not None else ""
        text = (
            f'/w {ingame_name} Hi! I want to {verb}: '
            f'{qty_prefix}"{name}{rank_part}" for {price} platinum.'
            f"{_MARKET_SUFFIX}"
        )

    return WhisperEntry(
        ingame_name=ingame_name,
        locale=locale,
        lang=lang,
        text=text,
        status=str(getattr(user, "status", "") or ""),
    )


def riven_whisper(
    auction,
    weapon_zh: str | None,
    weapon_en: str | None,
    fallback: str = "en",
) -> WhisperEntry | None:
    """紫卡拍卖 → 私聊语句（到紫卡名为止，不带词条与价格）。"""
    owner = getattr(auction, "owner", None)
    ingame_name = getattr(owner, "ingame_name", None) if owner else None
    if not ingame_name:
        return None

    locale = getattr(owner, "locale", None) or ""
    lang = pick_lang(locale, fallback)

    item = getattr(auction, "item", None)
    riven_name = (getattr(item, "name", None) or "").capitalize()

    if lang == "zh":
        weapon = weapon_zh or weapon_en or ""
        text = f"/w {ingame_name} 你好! 我想购买你的「{weapon}」紫卡 {riven_name}".rstrip()
    else:
        weapon = weapon_en or weapon_zh or ""
        text = f'/w {ingame_name} Hi! I want to buy your {weapon} riven "{riven_name}"'

    return WhisperEntry(
        ingame_name=ingame_name,
        locale=locale,
        lang=lang,
        text=text,
        status=str(getattr(owner, "status", "") or ""),
    )


def lich_whisper(
    auction,
    weapon_zh: str | None,
    weapon_en: str | None,
    fallback: str = "en",
) -> WhisperEntry | None:
    """玄骸/信条拍卖 → 私聊语句（带武器名与元素加成）。"""
    owner = getattr(auction, "owner", None)
    ingame_name = getattr(owner, "ingame_name", None) if owner else None
    if not ingame_name:
        return None

    locale = getattr(owner, "locale", None) or ""
    lang = pick_lang(locale, fallback)

    item = getattr(auction, "item", None)
    element = _element_name(getattr(item, "element", None), lang)
    damage = getattr(item, "damage", None)
    ephemera = bool(getattr(item, "having_ephemera", False))

    if lang == "zh":
        weapon = weapon_zh or weapon_en or ""
        bonus = f"（{damage}% {element}）" if damage is not None and element else ""
        extra = "（带幻纹）" if ephemera else ""
        text = f"/w {ingame_name} 你好! 我想购买你的「{weapon}」{bonus}{extra}"
    else:
        weapon = weapon_en or weapon_zh or ""
        bonus = f" ({damage}% {element})" if damage is not None and element else ""
        extra = " (with Ephemera)" if ephemera else ""
        text = f"/w {ingame_name} Hi! I want to buy your {weapon}{bonus}{extra}"

    return WhisperEntry(
        ingame_name=ingame_name,
        locale=locale,
        lang=lang,
        text=text,
        status=str(getattr(owner, "status", "") or ""),
    )


# ---------------------------------------------------------------- 会话缓存
@dataclass
class _Pick:
    expire_at: float
    source: str
    entries: list[WhisperEntry]


_picks: dict[str, _Pick] = {}


def _key(session: str, sender: str) -> str:
    return f"{session}:{sender}"


def remember(
    session: str,
    sender: str,
    source: str,
    entries: list[WhisperEntry],
) -> None:
    """记住本次卡片的私聊语句，供 ``/w <序号>`` 取用。

    Args:
        session: 会话标识（``unified_msg_origin``）。
        sender: 发送者 ID —— 群聊里不同人的卡片不能互相覆盖。
        source: 来源指令（``WM`` / ``WR`` / ``CD`` / ``XT``），仅用于提示。
        entries: 与卡片行一一对应的语句。
    """
    now = time.time()
    if entries:
        _picks[_key(session, sender)] = _Pick(now + PICK_TTL, source, list(entries))
    for key in [k for k, pick in _picks.items() if pick.expire_at < now]:
        _picks.pop(key, None)


def peek(session: str, sender: str) -> tuple[str, list[WhisperEntry]] | None:
    """查看当前缓存的（来源, 语句列表），过期返回 None。"""
    pick = _picks.get(_key(session, sender))
    if pick is None:
        return None
    if pick.expire_at < time.time():
        _picks.pop(_key(session, sender), None)
        return None
    return pick.source, pick.entries


def pop(session: str, sender: str, index: int) -> WhisperEntry | None:
    """取第 ``index`` 条（从 1 开始）；越界或过期返回 None。"""
    current = peek(session, sender)
    if current is None:
        return None
    _source, entries = current
    if not 1 <= index <= len(entries):
        return None
    return entries[index - 1]


def count(session: str, sender: str) -> int:
    """当前缓存的语句条数（无缓存返回 0）。"""
    current = peek(session, sender)
    return len(current[1]) if current else 0


def clear() -> None:
    """清空缓存（测试用）。"""
    _picks.clear()


USAGE = (
    "用法：/w <序号>\n"
    "序号来自上一张市场卡片（/WM /WR /CD /XT）最左列，2 分钟内有效。"
)


def reply_for(session: str, sender: str, raw: str) -> str:
    """把 ``/w`` 的参数解析成回复文本（纯函数，便于单测）。

    Args:
        session: 会话标识。
        sender: 发送者 ID。
        raw: 指令之后的文本，如 ``"3"``。

    Returns:
        要回复给用户的文本（可能含提示）。
    """
    text = (raw or "").strip()
    if not text:
        return USAGE

    head = text.split(" ", 1)[0]
    if not head.isdigit():
        return f"「{head}」不是序号。\n{USAGE}"

    index = int(head)
    total = count(session, sender)
    if total == 0:
        return (
            "还没有可用的私聊信息，请先查询：/WM 物品名 或 /WR 武器名"
            "（结果 2 分钟内有效）"
        )

    entry = pop(session, sender, index)
    if entry is None:
        return f"序号超出范围：共 {total} 条，请回 1~{total}"

    result = entry.text
    if entry.status == "offline":
        result += "\n（对方当前离线，可能收不到）"
    return result


def log_summary(entries: list[WhisperEntry], source: str) -> None:
    """打一条调试日志，便于排障时确认生成了多少条、语言分布。"""
    if not entries:
        return
    langs: dict[str, int] = {}
    for entry in entries:
        langs[entry.lang] = langs.get(entry.lang, 0) + 1
    logger.debug(f"{source} 私聊语句 {len(entries)} 条，语言分布 {langs}")
