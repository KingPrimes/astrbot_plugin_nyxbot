"""WorldState service / 世界状态服务层

负责 WorldState 数据的拉取、解析和缓存管理。
"""
from __future__ import annotations

from typing import Any

from tortoise.exceptions import DoesNotExist

from ..api.world_state import WorldStateClient
from ..model.export.nodes import Nodes
from ..util.cache_utils import async_cached, world_state_cache


class WorldStateService:
    """世界状态服务。

    提供对 Warframe 世界状态的访问，带有本地缓存。
    """

    CACHE_KEY = "world_state_raw"

    @classmethod
    async def get_raw(cls) -> dict[str, Any] | None:
        """获取原始 WorldState 数据（带缓存）。"""
        return await async_cached(
            cls.CACHE_KEY,
            lambda: WorldStateClient.fetch_raw(),
            world_state_cache,
        )

    @classmethod
    async def get_alerts(cls) -> list[dict]:
        """获取警报数据。"""
        raw = await cls.get_raw()
        if raw is None:
            return []
        return raw.get("Alerts", [])

    @classmethod
    async def get_sorties(cls) -> list[dict]:
        """获取突击数据。"""
        raw = await cls.get_raw()
        if raw is None:
            return []
        return raw.get("Sorties", [])

    @classmethod
    async def get_fissures(cls) -> list[dict]:
        """获取裂隙数据。"""
        raw = await cls.get_raw()
        if raw is None:
            return []
        return raw.get("Fissures", [])

    @classmethod
    async def get_invasions(cls) -> list[dict]:
        """获取入侵数据。"""
        raw = await cls.get_raw()
        if raw is None:
            return []
        return raw.get("Invasions", [])

    @classmethod
    async def get_void_trader(cls) -> dict | None:
        """获取虚空商人数据。"""
        raw = await cls.get_raw()
        if raw is None:
            return None
        traders = raw.get("VoidTraders", [])
        return traders[0] if traders else None

    @classmethod
    async def get_cetus_cycle(cls) -> dict | None:
        """获取希图斯周期。"""
        raw = await cls.get_raw()
        if raw is None:
            return None
        return raw.get("CetusCycle")

    @classmethod
    async def get_duviri_cycle(cls) -> dict | None:
        """获取双衍王境周期。"""
        raw = await cls.get_raw()
        if raw is None:
            return None
        return raw.get("DuviriCycle")

    @classmethod
    async def get_nightwave(cls) -> dict | None:
        """获取午夜电波数据。"""
        raw = await cls.get_raw()
        if raw is None:
            return None
        return raw.get("Nightwave")

    @classmethod
    async def get_daily_deals(cls) -> list[dict]:
        """获取每日特惠数据。"""
        raw = await cls.get_raw()
        if raw is None:
            return []
        return raw.get("DailyDeals", [])

    @classmethod
    async def get_steel_path(cls) -> dict | None:
        """获取钢铁之路数据。"""
        raw = await cls.get_raw()
        if raw is None:
            return None
        return raw.get("SteelPath")

    @classmethod
    async def get_arbitration(cls) -> dict | None:
        """获取仲裁数据。"""
        raw = await cls.get_raw()
        if raw is None:
            return None
        return raw.get("Arbitration")

    @classmethod
    def clear_cache(cls) -> None:
        """清除 WorldState 缓存。"""
        world_state_cache.clear()

    # ── 星图节点查询 ──────────────────────────────────────────────────

    @classmethod
    async def get_node_by_name(cls, name: str) -> Nodes | None:
        """根据节点名称查找星图节点。"""
        try:
            return await Nodes.get(name=name)
        except DoesNotExist:
            return None

    @classmethod
    async def get_node(cls, unique_name: str) -> Nodes | None:
        """根据唯一标识查找星图节点。"""
        try:
            return await Nodes.get(uniqueName=unique_name)
        except DoesNotExist:
            return None
