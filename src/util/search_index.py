"""Search index / 搜索索引

把「名称 → 实体引用」放进内存，支持精确、slug、拼音、前缀、包含五类查找，
用于替代 `UPPER(REPLACE(name, ' ', '')) LIKE %x%` 这类全表扫描。

索引共两类键：

- **拼音**：仅对含汉字的名称生成，包含全拼与首字母；索引与查询都先做模糊音
  归一化（zh→z、ch→c、sh→s、ang→an、eng→en、ing→in、n→l），保证同音/近音
  输入可命中（`冰松` → `冰凇`）。
- **slug**：与语言无关，未汉化的新物品只能靠它命中（`nagantaka` → `噬蛇弩`）。

设计见 ``plans/search_ux_design_2026-11-04.md`` 3.1 / 3.8 节；匹配链路（A~G）
在 ``src/service/smart_match.py``。
"""
from __future__ import annotations

import asyncio
import bisect
import re
from collections.abc import Iterable
from dataclasses import dataclass

from tortoise import Tortoise

from astrbot.api import logger

try:  # pragma: no cover - 依赖缺失时降级为「无拼音」
    from pypinyin import Style, lazy_pinyin
except ImportError:  # pragma: no cover
    Style = None  # type: ignore[assignment]
    lazy_pinyin = None  # type: ignore[assignment]

SOURCE_ORDERS = "orders"
SOURCE_RIVEN = "riven"
SOURCE_LICH = "lich"
SOURCE_RELIC = "relic"

KIND_NAME = "name"
KIND_REWARD = "reward"

_WS_RE = re.compile(r"\s+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
# 模糊音归一化：南方口音常见混淆，索引与查询用同一套规则，不会放大误命中
_FUZZY_RULES = (
    ("zh", "z"),
    ("ch", "c"),
    ("sh", "s"),
    ("ang", "an"),
    ("eng", "en"),
    ("ing", "in"),
    ("n", "l"),
)


def normalize_key(text: str) -> str:
    """名称比较键：去空白 + 小写 + 去掉间隔号。

    只用于比较，不改变展示名。`赤毒·布拉玛` 与 `赤毒布拉玛` 得到同一个键；
    `-` 保留（`MK1-Braton` 有意义）。
    """
    if not text:
        return ""
    return _WS_RE.sub("", text.strip().lower()).replace("·", "").replace("・", "")


def normalize_slug(slug: str) -> str:
    """slug 比较键：在 ``normalize_key`` 基础上去掉下划线。

    `frost_prime_set` → `frostprimeset`，与 `frost prime set` 同键。
    """
    return normalize_key(slug).replace("_", "")


def relic_name_key(name: str) -> str:
    """遗物名比较键：去掉统一的「遗物」后缀。

    `中纪 A1 遗物` 的键是 `中纪a1`，这样用户输入 `中纪 A1` 就是精确命中，
    而不是前缀命中 `中纪 A10/A11/...`。
    """
    key = normalize_key(name)
    return key[:-2] if key.endswith("遗物") else key


def has_cjk(text: str) -> bool:
    """是否包含汉字（决定要不要生成/查询拼音键）。"""
    return bool(text and _CJK_RE.search(text))


def fuzzy_pinyin(pinyin: str) -> str:
    """模糊音归一化（zh→z、ang→an、n→l 等）。"""
    for src, dst in _FUZZY_RULES:
        pinyin = pinyin.replace(src, dst)
    return pinyin


@dataclass(frozen=True)
class Entry:
    """索引条目：一条可搜索名称及其指向的实体。"""

    source: str
    """orders / riven / lich / relic"""
    ref: str
    """实体主键（orders/riven/lich 的 id，relic 的 uniqueName）"""
    name: str
    """展示名"""
    key: str
    """归一化比较键"""
    slug: str = ""
    """拼音之外的英文键（无则为空）"""
    kind: str = KIND_NAME
    """relic 专用：name=遗物名，reward=奖励名"""


class SearchIndex:
    """内存索引。构建一次约 0.4 s，常驻约 2 MB。"""

    def __init__(self) -> None:
        self._by_key: dict[str, list[Entry]] = {}
        self._by_slug: dict[str, list[Entry]] = {}
        self._by_pinyin: dict[str, list[Entry]] = {}
        self._by_initial: dict[str, list[Entry]] = {}
        self._sorted_keys: list[str] = []

    # ------------------------------------------------------------------ 构建
    @classmethod
    def build(cls, entries: Iterable[Entry]) -> SearchIndex:
        """由条目列表构建索引（CPU 密集，建议放线程里跑）。"""
        index = cls()
        seen: set[tuple[str, str, str, str]] = set()
        pinyin_cache: dict[str, tuple[str, str] | None] = {}

        for entry in entries:
            signature = (entry.source, entry.ref, entry.key, entry.kind)
            if signature in seen:
                continue
            seen.add(signature)

            index._by_key.setdefault(entry.key, []).append(entry)

            if entry.slug:
                slug_key = normalize_slug(entry.slug)
                if slug_key:
                    index._by_slug.setdefault(slug_key, []).append(entry)

            if not lazy_pinyin or not has_cjk(entry.name):
                continue
            cached = pinyin_cache.get(entry.name)
            if cached is None:
                syllables = [
                    s
                    for s in lazy_pinyin(entry.name, style=Style.NORMAL, errors="ignore")
                    if s
                ]
                cached = (
                    (
                        fuzzy_pinyin("".join(syllables)),
                        fuzzy_pinyin("".join(s[0] for s in syllables)),
                    )
                    if syllables
                    else None
                )
                pinyin_cache[entry.name] = cached
            if cached is None:
                continue
            index._by_pinyin.setdefault(cached[0], []).append(entry)
            index._by_initial.setdefault(cached[1], []).append(entry)

        index._sorted_keys = sorted(index._by_key)
        return index

    def stats(self) -> str:
        """日志用的摘要。"""
        return (
            f"名称键 {len(self._by_key)} / slug 键 {len(self._by_slug)} / "
            f"拼音键 {len(self._by_pinyin)} / 首字母键 {len(self._by_initial)}"
            + ("" if lazy_pinyin else "（未安装 pypinyin，拼音匹配不可用）")
        )

    # ------------------------------------------------------------------ 查询
    def exact(self, key: str) -> list[Entry]:
        """B：精确。"""
        return self._by_key.get(key, [])

    def by_slug(self, key: str) -> list[Entry]:
        """D：slug / 英文键。"""
        return self._by_slug.get(normalize_slug(key), [])

    def prefix(self, key: str, limit: int = 15) -> list[Entry]:
        """F1：前缀（二分定位，不扫全表）。"""
        if not key:
            return []
        start = bisect.bisect_left(self._sorted_keys, key)
        out: list[Entry] = []
        for i in range(start, len(self._sorted_keys)):
            name_key = self._sorted_keys[i]
            if not name_key.startswith(key):
                break
            out.extend(self._by_key[name_key])
            if len(out) >= limit:
                return out[:limit]
        return out

    def prefix_end(self, key: str, limit: int = 15) -> list[Entry]:
        """F2：前缀 + 末字符（对齐 Java/Go 的首末匹配）。

        前缀从 4 个字逐级放宽到 1 个；关键词 ≥4 字时前缀不再短于 3 个字，
        避免 `braton` 这类库里没有的名字因为首字母相同就落成 `Banshee Prime`。
        """
        if len(key) < 2:
            return []
        end = key[-1]
        min_prefix = 3 if len(key) >= 4 else 1
        for prefix_len in range(min(4, len(key) - 1), min_prefix - 1, -1):
            prefix_key = key[:prefix_len]
            start = bisect.bisect_left(self._sorted_keys, prefix_key)
            hits: list[Entry] = []
            for i in range(start, len(self._sorted_keys)):
                name_key = self._sorted_keys[i]
                if not name_key.startswith(prefix_key):
                    break
                if end in name_key[prefix_len:]:
                    hits.extend(self._by_key[name_key])
                    if len(hits) >= limit:
                        break
            if hits:
                return hits[:limit]
        return []

    def contains(self, key: str, limit: int = 15) -> list[Entry]:
        """F3：包含（唯一的线性扫描，5000 条约 0.2 ms）。"""
        if len(key) < 2:
            return []
        out: list[Entry] = []
        for name_key in self._sorted_keys:
            if key in name_key:
                out.extend(self._by_key[name_key])
                if len(out) >= limit:
                    return out[:limit]
        return out

    def pinyin(self, text: str, limit: int = 15) -> list[Entry]:
        """E：拼音。汉字输入先转拼音，ASCII 输入直接当拼音键查。"""
        compact = normalize_key(text)
        if not compact:
            return []

        if has_cjk(text):
            if not lazy_pinyin:
                return []
            syllables = [
                s for s in lazy_pinyin(text, style=Style.NORMAL, errors="ignore") if s
            ]
            if not syllables:
                return []
            full_key = fuzzy_pinyin("".join(syllables))
            initial_key = fuzzy_pinyin("".join(s[0] for s in syllables))
        else:
            if not compact.isascii():
                return []
            full_key = initial_key = fuzzy_pinyin(compact)

        # 全拼优先：全拼有结果时不再掺入首字母结果，避免短首字母带来的噪声
        out = list(self._by_pinyin.get(full_key, []))
        if not out:
            out = list(self._by_initial.get(initial_key, []))
        return _dedupe(out)[:limit]


def _dedupe(entries: Iterable[Entry]) -> list[Entry]:
    """按 (source, ref) 去重，保留首次出现的顺序。"""
    seen: set[tuple[str, str]] = set()
    out: list[Entry] = []
    for entry in entries:
        signature = (entry.source, entry.ref)
        if signature in seen:
            continue
        seen.add(signature)
        out.append(entry)
    return out


# ---------------------------------------------------------------- 全局单例
_index: SearchIndex | None = None
_build_lock: asyncio.Lock | None = None


async def _load_entries() -> list[Entry]:
    """从数据库读出全部可搜索名称。"""
    conn = Tortoise.get_connection("default")
    entries: list[Entry] = []

    item_sources = (
        ("SELECT id, name, slug FROM ordersitems", SOURCE_ORDERS),
        ("SELECT id, name, slug FROM rivenitems", SOURCE_RIVEN),
        ("SELECT id, name, slug FROM lichsisterweapons", SOURCE_LICH),
    )
    for sql, source in item_sources:
        for row in await conn.execute_query_dict(sql):
            name = row.get("name") or ""
            key = normalize_key(name)
            if not key:
                continue
            entries.append(
                Entry(
                    source=source,
                    ref=str(row["id"]),
                    name=name,
                    key=key,
                    slug=row.get("slug") or "",
                )
            )

    for row in await conn.execute_query_dict(
        "SELECT uniqueName, name FROM relics"
    ):
        name = row.get("name") or ""
        key = relic_name_key(name)
        if not key:
            continue
        entries.append(
            Entry(
                source=SOURCE_RELIC,
                ref=str(row["uniqueName"]),
                name=name,
                key=key,
            )
        )

    # 奖励名 → 包含它的遗物（一个奖励可能出现在多个遗物里）
    for row in await conn.execute_query_dict(
        "SELECT rr.rewardName AS name, m.relics_id AS relic_id "
        "FROM relicrewards rr "
        "JOIN relics_relicrewards m ON m.relicrewards_id = rr.id"
    ):
        name = row.get("name") or ""
        key = normalize_key(name)
        if not key:
            continue
        entries.append(
            Entry(
                source=SOURCE_RELIC,
                ref=str(row["relic_id"]),
                name=name,
                key=key,
                kind=KIND_REWARD,
            )
        )

    return entries


async def get_index() -> SearchIndex:
    """取索引，首次调用时构建（线程池执行，构建约 0.4 s）。"""
    global _index, _build_lock
    if _index is not None:
        return _index

    if _build_lock is None:
        _build_lock = asyncio.Lock()
    async with _build_lock:
        if _index is None:
            entries = await _load_entries()
            index = await asyncio.to_thread(SearchIndex.build, entries)
            _index = index
            logger.info(f"搜索索引构建完成：{len(entries)} 条名称，{index.stats()}")
    return _index


def invalidate() -> None:
    """数据导入/刷新后调用，下次查询时重建。"""
    global _index
    if _index is not None:
        logger.debug("搜索索引已失效，下次查询时重建")
    _index = None
