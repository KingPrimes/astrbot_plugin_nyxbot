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

from ..util.alias_cache import AliasCacheHelper
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


_alias_helper = AliasCacheHelper()


def _prime_variant(key: str) -> str:
    """把简写 `p` 展开成 `prime`（对齐 Java/Go 的 processPrimeKeyword）。

    仅在关键词不含 ``prime`` 且含 ``p`` 时替换；`braton` 这类含 p 的完整名
    会得到 `braton` → `brat on`? 不会——替换的是字母 p，`braton` 没有 p，
    所以只有 `volt p`、`emberp` 这类输入才会走到这里。
    """
    if key and "prime" not in key and "p" in key:
        return key.replace("p", "prime")
    return key


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

    ASCII 输入常是英文名的缩写或拼错（`braton`、`volt p`），首字母兜底能给出
    有用的候选；中文首字信息密度低（`冰队` 会兜出 `冰凇`），只在输入本身
    就是一个字（`/WM 冰`）时才允许，否则返回「未找到」更诚实。
    """
    if not key:
        return False
    return key.isascii() or len(key) == 1


_PART_TOKENS = (
    "头部神经光元", "头盔", "头",
    "机体", "机",
    "系统", "系",
    "蓝图", "总图", "图",
    "一套", "套",
    "blueprint", "chassis", "systems", "system", "neuroptics", "helmet", "set",
)
"""部位/形态词。出现这些词说明用户要的是某个部件，不该被「套装优先」劫持。"""


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
    is_set = (top.slug or "").endswith("set")
    # query_key 为空表示调用方不参与「套装优先」判断（拼音阶段）
    set_preferred = bool(query_key) and not _has_part_token(query_key)
    if len(ranked) == 1 or (is_set and set_preferred):
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

    def pick(entries: list[Entry]) -> list[Entry]:
        return [entry for entry in entries if entry.source == source]

    # B 精确 / C 别名（变体顺序即优先级；精确命中即使有重名也取第一条）
    for position, variant in enumerate(variants):
        hits = pick(index.exact(variant))
        if hits:
            stage = "B" if position == 0 else "C"
            logger.debug(f"[{stage}] {raw!r} → {hits[0].name!r}")
            return Hit(hits[0], stage)

    # D slug（仅纯 ASCII；未汉化物品靠它）
    if key.isascii():
        result = _decide(pick(index.by_slug(key)), "D", key)
        if result:
            logger.debug(f"[D] {raw!r} → {result}")
            return result
        # D2：英文部件名在库里带 _blueprint 后缀，用户通常不会打全
        result = _decide(pick(index.slug_prefix(key)), "D", key)
        if result:
            logger.debug(f"[D2] {raw!r} → {result}")
            return result

    # F 前缀 / 首末 / 包含
    for position, variant in enumerate(variants):
        hits: list[Entry] = []
        for finder in (index.prefix, index.prefix_end, index.contains):
            hits = pick(finder(variant))
            if hits:
                break
        result = _decide(hits, "F" if position == 0 else "C", variant)
        if result:
            logger.debug(f"[F] {raw!r} → {result}")
            return result

    # E 拼音（只对原文；别名已经是英文，再转拼音没有意义）
    result = _decide(pick(index.pinyin(raw)), "E")
    if result:
        logger.debug(f"[E] {raw!r} → {result}")
        return result

    # G 候选：汇总 F / E 的结果，再退到「同首字符」
    pool: list[Entry] = []
    for variant in variants:
        pool.extend(pick(index.prefix(variant)))
        pool.extend(pick(index.prefix_end(variant)))
        pool.extend(pick(index.contains(variant)))
    pool.extend(pick(index.pinyin(raw)))
    if not pool and _allow_first_char_fallback(key):
        pool = pick(index.prefix(key[:1]))

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

    def relics(entries: list[Entry], kind: str) -> list[Entry]:
        return [
            entry
            for entry in entries
            if entry.source == SOURCE_RELIC and entry.kind == kind
        ]

    def finish(entries: list[Entry]) -> list[Entry]:
        return sorted(_dedupe(entries), key=lambda e: e.name)

    # B 遗物名精确
    for variant in variants:
        hits = relics(index.exact(variant), KIND_NAME)
        if hits:
            return finish(hits)

    # R1 奖励名精确
    for variant in variants:
        hits = relics(index.exact(variant), KIND_REWARD)
        if hits:
            return finish(hits)

    # R2 / F 前缀 / 首末 / 包含（结果集，放宽上限避免截断）
    for kind in (KIND_REWARD, KIND_NAME):
        hits: list[Entry] = []
        for variant in variants:
            for finder in (index.prefix, index.prefix_end, index.contains):
                hits.extend(relics(finder(variant, _RELIC_LIMIT), kind))
        if hits:
            return finish(hits)

    # E 拼音
    return finish(relics(index.pinyin(raw, _RELIC_LIMIT), KIND_NAME))


# ---------------------------------------------------------------- 候选记忆
_candidates: dict[str, tuple[float, list[str]]] = {}


def remember_candidates(session: str, names: list[str]) -> None:
    """记住本次候选，供 60 秒内用编号回选。"""
    if not names:
        return
    now = time.time()
    _candidates[session] = (now + CANDIDATE_TTL, list(names))
    for key in [k for k, (expire_at, _) in _candidates.items() if expire_at < now]:
        _candidates.pop(key, None)


def resolve_selection(session: str, text: str) -> str | None:
    """把开头的「编号」替换成候选名称；不是编号或已过期则返回 None。

    保留编号之后的其余参数，这样 ``/WM 1 满级 PC`` 仍能带上满级和平台。
    """
    raw = (text or "").strip()
    if not raw:
        return None

    head, _, tail = raw.partition(" ")
    if not head.isdigit():
        return None

    cached = _candidates.get(session)
    if cached is None:
        return None

    expire_at, names = cached
    if expire_at < time.time():
        _candidates.pop(session, None)
        return None

    index = int(head)
    if not 1 <= index <= len(names):
        return None

    name = names[index - 1]
    return f"{name} {tail.strip()}".strip() if tail.strip() else name
