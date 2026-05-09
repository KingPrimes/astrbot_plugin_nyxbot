"""Cache utilities / 缓存工具

基于 cachetools.TTLCache 的轻量级缓存封装。
"""
from __future__ import annotations

from cachetools import TTLCache
from typing import Any, Callable, TypeVar

T = TypeVar("T")

# ============================================================================
# 全局缓存实例 / Global Cache Instances
# ============================================================================

# WorldState 缓存：最多缓存 1 份完整数据，5 分钟过期
world_state_cache: TTLCache[str, Any] = TTLCache(maxsize=1, ttl=300)

# Market API 查询缓存：最多 50 个查询条件，**2 分钟固定过期**
# Market API 有频率限制，2 分钟 TTL 确保数据时效性同时避免触发限流
market_cache: TTLCache[str, Any] = TTLCache(maxsize=50, ttl=120)

# Market 搜索结果缓存：最多 200 个独立搜索词，2 分钟过期
market_search_cache: TTLCache[str, Any] = TTLCache(maxsize=200, ttl=120)

# 通用缓存（可自定义 TTL）
_general_caches: dict[str, TTLCache] = {}


def get_cache(name: str, maxsize: int = 100, ttl: int = 300) -> TTLCache:
    """获取或创建指定名称的缓存实例。

    Args:
        name: 缓存名称。
        maxsize: 最大条目数。
        ttl: 过期时间（秒）。

    Returns:
        TTLCache 实例。
    """
    if name not in _general_caches:
        _general_caches[name] = TTLCache(maxsize=maxsize, ttl=ttl)
    return _general_caches[name]


def cached(key: str, fetch_func: Callable[[], T], cache: TTLCache) -> T:
    """缓存装饰器模式：缓存命中则返回，否则调用 fetch_func 获取并缓存。

    Args:
        key: 缓存键。
        fetch_func: 数据获取函数。
        cache: 使用的缓存实例。

    Returns:
        缓存或获取的数据。
    """
    if key in cache:
        return cache[key]
    value = fetch_func()
    cache[key] = value
    return value


async def async_cached(key: str, fetch_func: Callable[[], Any], cache: TTLCache) -> Any:
    """异步版本的缓存装饰器模式。

    Args:
        key: 缓存键。
        fetch_func: 异步数据获取函数。
        cache: 使用的缓存实例。

    Returns:
        缓存或获取的数据。
    """
    if key in cache:
        return cache[key]
    value = await fetch_func()
    cache[key] = value
    return value
