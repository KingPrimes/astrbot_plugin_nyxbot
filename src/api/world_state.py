"""WorldState API client / 世界状态 API 客户端

封装 Warframe 世界状态 API 的请求和响应解析。
"""
from __future__ import annotations

from typing import Any, Optional

from ..util import fetch_json


class WorldStateClient:
    """Warframe 世界状态 API 客户端。

    用于拉取 WorldState 数据，包括警报、突击、裂隙、入侵等所有世界状态信息。
    """

    BASE_URL = "https://api.warframe.com/cdn/worldState.php"

    @classmethod
    async def fetch_raw(cls) -> Optional[dict[str, Any]]:
        """拉取原始 WorldState 数据。

        Returns:
            原始 JSON 字典，失败返回 None。
        """
        return await fetch_json(cls.BASE_URL, content_type=None)

    @classmethod
    async def get_alerts(cls, raw_data: Optional[dict] = None) -> list[dict]:
        """获取警报数据。

        Args:
            raw_data: 可选的已拉取的原始数据，避免重复请求。

        Returns:
            警报列表。
        """
        if raw_data is None:
            raw_data = await cls.fetch_raw()
        if raw_data is None:
            return []
        return raw_data.get("Alerts", [])

    @classmethod
    async def get_sorties(cls, raw_data: Optional[dict] = None) -> list[dict]:
        """获取突击数据。"""
        if raw_data is None:
            raw_data = await cls.fetch_raw()
        if raw_data is None:
            return []
        return raw_data.get("Sorties", [])

    @classmethod
    async def get_fissures(cls, raw_data: Optional[dict] = None) -> list[dict]:
        """获取裂隙数据。"""
        if raw_data is None:
            raw_data = await cls.fetch_raw()
        if raw_data is None:
            return []
        return raw_data.get("Fissures", [])

    @classmethod
    async def get_invasions(cls, raw_data: Optional[dict] = None) -> list[dict]:
        """获取入侵数据。"""
        if raw_data is None:
            raw_data = await cls.fetch_raw()
        if raw_data is None:
            return []
        return raw_data.get("Invasions", [])

    @classmethod
    async def get_void_trader(cls, raw_data: Optional[dict] = None) -> Optional[dict]:
        """获取虚空商人数据。"""
        if raw_data is None:
            raw_data = await cls.fetch_raw()
        if raw_data is None:
            return None
        traders = raw_data.get("VoidTraders", [])
        return traders[0] if traders else None

    @classmethod
    async def get_cetus_cycle(cls, raw_data: Optional[dict] = None) -> Optional[dict]:
        """获取希图斯周期。"""
        if raw_data is None:
            raw_data = await cls.fetch_raw()
        if raw_data is None:
            return None
        return raw_data.get("CetusCycle")

    @classmethod
    async def get_duviri_cycle(cls, raw_data: Optional[dict] = None) -> Optional[dict]:
        """获取双衍王境周期。"""
        if raw_data is None:
            raw_data = await cls.fetch_raw()
        if raw_data is None:
            return None
        return raw_data.get("DuviriCycle")

    @classmethod
    async def get_nightwave(cls, raw_data: Optional[dict] = None) -> Optional[dict]:
        """获取午夜电波数据。"""
        if raw_data is None:
            raw_data = await cls.fetch_raw()
        if raw_data is None:
            return None
        return raw_data.get("Nightwave")

    @classmethod
    async def get_daily_deals(cls, raw_data: Optional[dict] = None) -> list[dict]:
        """获取每日特惠数据。"""
        if raw_data is None:
            raw_data = await cls.fetch_raw()
        if raw_data is None:
            return []
        return raw_data.get("DailyDeals", [])

    @classmethod
    async def get_steel_path(cls, raw_data: Optional[dict] = None) -> Optional[dict]:
        """获取钢铁之路数据。"""
        if raw_data is None:
            raw_data = await cls.fetch_raw()
        if raw_data is None:
            return None
        return raw_data.get("SteelPath")

    @classmethod
    async def get_arbitration(cls, raw_data: Optional[dict] = None) -> Optional[dict]:
        """获取仲裁数据。"""
        if raw_data is None:
            raw_data = await cls.fetch_raw()
        if raw_data is None:
            return None
        return raw_data.get("Arbitration")
