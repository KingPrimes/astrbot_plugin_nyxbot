"""Alias cache helper / 别名缓存辅助类

封装别名缓存的双重检查锁 + 预编译正则替换，
消除 market_orders.py 和 relics.py 中的重复模式。
"""
from __future__ import annotations

import asyncio
import re

from ..model.alias import Alias


class AliasCacheHelper:
    """别名缓存 + 预编译正则替换。

    使用双重检查锁确保并发安全的一次性加载，
    预编译正则按最长匹配优先替换中文别名为英文。

    用法::

        _alias_helper = AliasCacheHelper()

        async def process(keyword: str) -> str:
            return await _alias_helper.replace(keyword)
    """

    def __init__(self) -> None:
        self._cache: list[Alias] | None = None
        self._lock: asyncio.Lock | None = None
        self._regex: re.Pattern | None = None
        self._map: dict[str, str] = {}

    async def _ensure_loaded(self) -> None:
        """双重检查锁：仅在首次调用时全表加载并编译正则。"""
        if self._cache is None:
            if self._lock is None:
                self._lock = asyncio.Lock()
            async with self._lock:
                if self._cache is None:
                    self._cache = await Alias.all() or []
                    sorted_pairs = sorted(
                        ((a.cn, a.en) for a in self._cache if a.cn and a.en),
                        key=lambda x: len(x[0]), reverse=True,
                    )
                    self._map = dict(sorted_pairs)
                    self._regex = re.compile(
                        "|".join(re.escape(cn) for cn, _ in sorted_pairs)
                    ) if sorted_pairs else re.compile(r"(?!)")

    async def replace(self, text: str) -> str:
        """将文本中的中文别名替换为英文。

        Args:
            text: 待替换的文本。

        Returns:
            替换后的文本。若无匹配别名则原样返回。
        """
        await self._ensure_loaded()
        if self._regex is None:
            return text
        return self._regex.sub(lambda m: self._map[m.group()], text)

    def invalidate(self) -> None:
        """丢弃缓存，下次调用时重新加载。

        别名同步、管理页增删改之后必须调用，否则新增/删除的别名要重启才生效。
        """
        self._cache = None
        self._regex = None
        self._map = {}


_default_helper = AliasCacheHelper()
"""进程内共享的别名缓存：搜索链路与旧调用点共用同一份，便于统一失效。"""


def get_alias_helper() -> AliasCacheHelper:
    """取共享的别名缓存实例。"""
    return _default_helper


def invalidate_alias_cache() -> None:
    """数据变更后丢弃别名缓存。"""
    _default_helper.invalidate()
