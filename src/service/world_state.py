"""WorldState service / 世界状态服务层

负责 WorldState 数据的拉取、解析和缓存管理。
"""
from __future__ import annotations

from typing import Any, Optional

from ..api import WorldStateClient
from ..util import world_state_cache, async_cached


class WorldStateService:
    """世界状态服务。

    提供对 Warframe 世界状态的访问，带有本地缓存。
    """

    CACHE_KEY = "world_state_raw"

    @classmethod
    async def get_raw(cls) -> Optional[dict[str, Any]]:
        """获取原始 WorldState 数据（带缓存）。"""
        return await async_cached(
            cls.CACHE_KEY,
            WorldStateClient.fetch_raw,
            world_state_cache,
        )

    @classmethod
    async def get_alerts(cls) -> list[dict]:
        """获取警报数据。"""
        raw = await cls.get_raw()
        if not raw:
            return []
        return await WorldStateClient.get_alerts(raw)

    @classmethod
    async def get_sorties(cls) -> list[dict]:
        """获取突击数据。"""
        raw = await cls.get_raw()
        if not raw:
            return []
        return await WorldStateClient.get_sorties(raw)

    @classmethod
    async def get_fissures(cls) -> list[dict]:
        """获取裂隙数据。"""
        raw = await cls.get_raw()
        if not raw:
            return []
        return await WorldStateClient.get_fissures(raw)

    @classmethod
    async def get_invasions(cls) -> list[dict]:
        """获取入侵数据。"""
        raw = await cls.get_raw()
        if not raw:
            return []
        return await WorldStateClient.get_invasions(raw)

    @classmethod
    async def get_void_trader(cls) -> Optional[dict]:
        """获取虚空商人数据。"""
        raw = await cls.get_raw()
        if not raw:
            return None
        return await WorldStateClient.get_void_trader(raw)

    @classmethod
    async def get_cetus_cycle(cls) -> Optional[dict]:
        """获取希图斯周期。"""
        raw = await cls.get_raw()
        if not raw:
            return None
        return await WorldStateClient.get_cetus_cycle(raw)

    @classmethod
    async def get_duviri_cycle(cls) -> Optional[dict]:
        """获取双衍王境周期。"""
        raw = await cls.get_raw()
        if not raw:
            return None
        return await WorldStateClient.get_duviri_cycle(raw)

    @classmethod
    async def get_nightwave(cls) -> Optional[dict]:
        """获取午夜电波数据。"""
        raw = await cls.get_raw()
        if not raw:
            return None
        return await WorldStateClient.get_nightwave(raw)

    @classmethod
    async def get_daily_deals(cls) -> list[dict]:
        """获取每日特惠数据。"""
        raw = await cls.get_raw()
        if not raw:
            return []
        return await WorldStateClient.get_daily_deals(raw)

    @classmethod
    async def get_steel_path(cls) -> Optional[dict]:
        """获取钢铁之路数据。"""
        raw = await cls.get_raw()
        if not raw:
            return None
        return await WorldStateClient.get_steel_path(raw)

    @classmethod
    async def get_arbitration(cls) -> Optional[dict]:
        """获取仲裁数据。"""
        raw = await cls.get_raw()
        if not raw:
            return None
        return await WorldStateClient.get_arbitration(raw)

    @classmethod
    def clear_cache(cls) -> None:
        """清除 WorldState 缓存。"""
        if cls.CACHE_KEY in world_state_cache:
            del world_state_cache[cls.CACHE_KEY]
