"""Smart match / 统一名称解析

把用户输入解析成具体实体，链路固定为 **A → G**（见
``plans/search_ux_design_2026-11-04.md`` 3.2 节）：

===========  ==========================================================
A 归一化      去空白/小写/去间隔号，生成别名与 Prime 变体
B 精确        比较键与名称逐字相等
C 别名        ``alias`` 表（冰队 → Frost）替换后再匹配
D slug        slug 去下划线后整串相等，未汉化物品的唯一可用键
E 拼音        全拼 / 首字母 / 模糊音，整串相等
F 前缀/首末    前缀二分 → 前缀+末字符 → 包含
G 候选        ≤15 条，交给指令层做编号选择
===========  ==========================================================

两种输入形态的差别只有两处：D 只对纯 ASCII 生效；B 在两种形态下分别命中
中文名与英文名。所有匹配都在内存索引里完成，不再 `LIKE %x%` 扫全表。
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum

from astrbot.api import logger

from ..util.alias_cache import get_alias_helper
from ..util.search_index import (
    KIND_NAME,
    KIND_REWARD,
    SOURCE_LICH,
    SOURCE_ORDERS,
    SOURCE_RELIC,
    SOURCE_RIVEN,
    Entry,
    get_index,
    normalize_key,
)

CANDIDATE_TTL = 60.0
"""候选记忆有效期（秒）。"""

_RELIC_LIMIT = 200
"""遗物是「结果集」而非「候选」，命中上限放宽，避免截断。"""


class Source(StrEnum):
    """数据源。"""

    ORDERS = SOURCE_ORDERS
    RIVEN = SOURCE_RIVEN
    LICH = SOURCE_LICH
    RELIC = SOURCE_RELIC


@dataclass
class Hit:
    """唯一命中。"""

    entry: Entry
    stage: str
    """B / C / D / E / F"""


@dataclass
class Candidates:
    """多个候选，交给指令层出编号列表。"""

    entries: list[Entry]
    stage: str = "G"


_alias_helper = get_alias_helper()


def _prime_variant(key: str) -> str:
    """把简写 `p` 展开成 `prime`（对齐 Java/Go 的 processPrimeKeyword）。

    仅在关键词不含 ``prime`` 且含 ``p`` 时替换；`braton` 这类含 p 的完整名
    会得到 `braton` → `brat on`? 不会——替换的是字母 p，`braton` 没有 p，
    所以只有 `volt p`、`emberp` 这类输入才会走到这里。
    """
    if key and "prime" not in key and "p" in key:
        return key.replace("p", "prime")
    return key


def _prime_inserted(text: str) -> str:
    """把 `banshee chassis` 补成 `banshee prime chassis`。

    库里 slug 是 ``banshee_prime_chassis_blueprint``，用户查部件时通常只写
    `banshee chassis`（省掉 Prime），整串相等与前缀都对不上，只能落到候选。
    仅对「纯 ASCII + 有空格 + 不含 prime」的输入补一版。
    """
    raw = " ".join((text or "").split())
    if not raw or not raw.isascii() or " " not in raw or "prime" in raw.lower():
        return ""
    head, _, tail = raw.partition(" ")
    return normalize_key(f"{head} prime {tail}")


async def _variants(text: str) -> list[str]:
    """A 阶段的产物：原文键 + 别名键 + Prime 变体键（去重保序）。"""
    key = normalize_key(text)
    variants = [key] if key else []

    aliased = normalize_key(await _alias_helper.replace(text.strip()))
    if aliased and aliased not in variants:
        variants.append(aliased)

    base = aliased or key
    primed = _prime_variant(base)
    if primed and primed not in variants:
        variants.append(primed)

    inserted = _prime_inserted(text)
    if inserted and inserted not in variants:
        variants.append(inserted)

    return variants


def _rank(entries: list[Entry]) -> list[Entry]:
    """候选排序：套装优先，其次名称短的（更可能是用户想要的）。"""
    return sorted(
        entries,
        key=lambda e: (
            0 if (e.slug or "").endswith("set") else 1,
            len(e.name),
            e.name,
        ),
    )


def _dedupe(entries: list[Entry]) -> list[Entry]:
    """按 (source, ref) 去重，保留首次出现顺序。"""
    seen: set[tuple[str, str]] = set()
    out: list[Entry] = []
    for entry in entries:
        signature = (entry.source, entry.ref)
        if signature in seen:
            continue
        seen.add(signature)
        out.append(entry)
    return out


def _allow_first_char_fallback(key: str) -> bool:
    """G 的「同首字符」兜底是否可用。

    ASCII 短输入常是英文名的缩写（`fro`、`volt`），首字母兜底能给出有用的候选；
    但长输入（`kuva bramma` 这类库里没有的名字）兜出来的是完全无关的物品
    （`k` → `Khora Prime 一套`），不如直接说没找到。中文首字信息密度低
    （`冰队` 会兜出 `冰凇`），只在输入本身就是一个字时允许。
    """
    if not key:
        return False
    if len(key) == 1:
        return True
    return key.isascii() and len(key) <= 4


_PART_TOKENS = (
    "头部神经光元", "头盔", "头",
    "机体", "机",
    "系统", "系",
    "蓝图", "总图", "图",
    "blueprint", "chassis", "systems", "system", "neuroptics", "helmet",
)
"""部位/形态词。出现这些词说明用户要的是某个部件，不该被「套装优先」劫持。

注意不能把「套 / 一套 / set」放进来：它们表示用户**就是要套装**，
放进来反而会关掉套装优先，``/WM frost set`` 会退化成候选。
"""


def _has_part_token(key: str) -> bool:
    """查询里是否带部位词（``冰队蓝图``、``frost prime chassis``）。"""
    return any(token in key for token in _PART_TOKENS)


def _decide(
    entries: list[Entry], stage: str, query_key: str = ""
) -> Hit | Candidates | None:
    """命中判定。

    - 只有一个实体 → ``Hit``；
    - 多个实体但排序第一的是**套装**，且查询里没有部位词 → 直接给套装
      （``冰队`` / ``embp`` / ``frost prime`` 要的就是整套）；
    - 其余多命中 → ``Candidates``，交给编号选择。
    """
    unique = _dedupe(entries)
    if not unique:
        return None

    ranked = _rank(unique)
    top = ranked[0]
    sets = [entry for entry in ranked if (entry.slug or "").endswith("set")]
    # query_key 为空表示调用方不参与「套装优先」判断（拼音阶段）；
    # 命中多个套装时（Braton Prime / Braton 破坏者）不猜，交给用户选编号
    set_preferred = bool(query_key) and not _has_part_token(query_key) and len(sets) == 1
    if len(ranked) == 1 or (top in sets and set_preferred):
        return Hit(top, stage)
    return Candidates(ranked[:15], stage)


async def resolve(text: str, source: Source) -> Hit | Candidates | None:
    """按 A~G 链路解析名称。

    Args:
        text: 指令之后、已剥离参数（满级/买卖/平台/词条）的名称文本。
        source: 目标数据源。

    Returns:
        ``Hit`` 唯一命中；``Candidates`` 多候选；``None`` 完全没找到。
    """
    raw = (text or "").strip()
    if not raw:
        return None

    index = await get_index()
    variants = await _variants(raw)
    if not variants:
        return None
    key = variants[0]

    def only(entry: Entry) -> bool:
        """索引先筛后截断：只让目标数据源的条目占用 limit。"""
        return entry.source == source

    # B 精确 / C 别名（变体顺序即优先级；精确命中即使有重名也取第一条）
    for position, variant in enumerate(variants):
        hits = index.exact(variant, only)
        if hits:
            stage = "B" if position == 0 else "C"
            logger.debug(f"[{stage}] {raw!r} → {hits[0].name!r}")
            return Hit(hits[0], stage)

    # D slug（仅纯 ASCII 输入；未汉化物品靠它）
    # 只看原文与 Prime 补全变体：中文输入（冰队）走 F 阶段的别名变体，
    # 否则 `frost` 会在 D 里命中，日志阶段会从 C 变成 D。
    if key.isascii():
        for variant in variants:
            if not variant.isascii():
                continue
            result = _decide(index.by_slug(variant, only), "D", variant)
            if result:
                logger.debug(f"[D] {raw!r} → {result}")
                return result
            # D2：英文部件名在库里带 _blueprint 后缀，用户通常不会打全
            result = _decide(index.slug_prefix(variant, match=only), "D", variant)
            if result:
                logger.debug(f"[D2] {raw!r} → {result}")
                return result

    # F 前缀 / 首末 / 包含
    for position, variant in enumerate(variants):
        hits: list[Entry] = []
        for finder in (index.prefix, index.prefix_end, index.contains):
            hits = finder(variant, match=only)
            if hits:
                break
        result = _decide(hits, "F" if position == 0 else "C", variant)
        if result:
            logger.debug(f"[F] {raw!r} → {result}")
            return result

    # E 拼音（只对原文；别名已经是英文，再转拼音没有意义）
    result = _decide(index.pinyin(raw, match=only), "E")
    if result:
        logger.debug(f"[E] {raw!r} → {result}")
        return result

    # G 候选：汇总 F / E 的结果，再退到「同首字符」
    pool: list[Entry] = []
    for variant in variants:
        pool.extend(index.prefix(variant, match=only))
        pool.extend(index.prefix_end(variant, match=only))
        pool.extend(index.contains(variant, match=only))
    pool.extend(index.pinyin(raw, match=only))
    if not pool and _allow_first_char_fallback(key):
        pool = index.prefix(key[:1], match=only)

    pool = _rank(_dedupe(pool))
    if pool:
        logger.debug(f"[G] {raw!r} → {len(pool)} 个候选")
        return Candidates(pool[:15])
    return None


async def resolve_relic(text: str) -> list[Entry]:
    """`/遗物` 专用解析：遗物名优先，其次奖励名。

    Returns:
        遗物条目列表（同一遗物去重）。单条即精确命中，多条即结果集。
    """
    raw = (text or "").strip()
    if not raw:
        return []

    index = await get_index()
    # 遗物名统一带「遗物」后缀，输入里带不带都能对上同一批键
    variants = [
        v[:-2] if v.endswith("遗物") else v for v in await _variants(raw)
    ]
    if not variants:
        return []

    def relic_only(kind: str):
        """索引先筛后截断：只让指定类型的遗物条目占用 limit。"""

        def match(entry: Entry) -> bool:
            return entry.source == SOURCE_RELIC and entry.kind == kind

        return match

    def finish(entries: list[Entry]) -> list[Entry]:
        return sorted(_dedupe(entries), key=lambda e: e.name)

    # B 遗物名精确
    for variant in variants:
        hits = index.exact(variant, relic_only(KIND_NAME))
        if hits:
            return finish(hits)

    # R1 奖励名精确
    for variant in variants:
        hits = index.exact(variant, relic_only(KIND_REWARD))
        if hits:
            return finish(hits)

    # R2 / F 前缀 / 首末 / 包含（结果集，放宽上限避免截断）
    for kind in (KIND_REWARD, KIND_NAME):
        match = relic_only(kind)
        hits: list[Entry] = []
        for variant in variants:
            for finder in (index.prefix, index.prefix_end, index.contains):
                hits.extend(finder(variant, _RELIC_LIMIT, match))
        if hits:
            return finish(hits)

    # E 拼音
    return finish(index.pinyin(raw, _RELIC_LIMIT, relic_only(KIND_NAME)))


# ---------------------------------------------------------------- 候选记忆
_candidates: dict[str, tuple[float, list[str]]] = {}


def _candidate_key(session: str, command: str) -> str:
    """候选缓存键：会话 + 指令。

    只按会话存的话，同一群 60 秒内先 `/WM 冰` 再 `/WR 1`，`/WR 1` 会拿到
    WM 的候选列表（战甲名），查出来是「未找到」或无关结果。
    """
    return f"{session}:{command}" if command else session


def remember_candidates(session: str, names: list[str], command: str = "") -> None:
    """记住本次候选，供 60 秒内用编号回选。

    Args:
        session: 会话标识（`unified_msg_origin`）。
        names: 候选名称，顺序即编号。
        command: 指令名（`WM` / `WR` / `CD` / `XT`），不同指令各存各的。
    """
    if not names:
        return
    now = time.time()
    _candidates[_candidate_key(session, command)] = (now + CANDIDATE_TTL, list(names))
    for key in [k for k, (expire_at, _) in _candidates.items() if expire_at < now]:
        _candidates.pop(key, None)


def resolve_selection(session: str, text: str, command: str = "") -> str | None:
    """把开头的「编号」替换成候选名称；不是编号或已过期则返回 None。

    保留编号之后的其余参数，这样 ``/WM 1 满级 PC`` 仍能带上满级和平台。
    """
    raw = (text or "").strip()
    if not raw:
        return None

    head, _, tail = raw.partition(" ")
    if not head.isdigit():
        return None

    key = _candidate_key(session, command)
    cached = _candidates.get(key)
    if cached is None:
        return None

    expire_at, names = cached
    if expire_at < time.time():
        _candidates.pop(key, None)
        return None

    index = int(head)
    if not 1 <= index <= len(names):
        return None

    name = names[index - 1]
    return f"{name} {tail.strip()}".strip() if tail.strip() else name
