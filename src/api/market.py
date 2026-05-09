"""Market API client / Warframe.Market API 客户端

封装 Warframe.Market API v2 的请求接口。
所有查询结果缓存在本地（TTLCache，2 分钟过期）。
"""
from __future__ import annotations

from typing import Any, Optional

from ..util import fetch_json, market_cache


class MarketClient:
    """Warframe.Market API 客户端。

    所有公共查询方法均带有 2 分钟本地缓存，避免触发 API 频率限制。
    """

    BASE_URL = "https://api.warframe.market/v2"
    AUCTIONS_URL = "https://api.warframe.market/v1/auctions"

    @classmethod
    async def _fetch_with_cache(cls, url: str, cache_key: str) -> Optional[Any]:
        """带缓存的 GET 请求（2 分钟 TTL）。

        Args:
            url: 请求 URL。
            cache_key: 缓存键。

        Returns:
            API 返回的 payload 数据，失败返回 None。
        """
        if cache_key in market_cache:
            return market_cache[cache_key]

        data = await fetch_json(url, headers={"Content-Type": "application/json"})
        if data and "payload" in data:
            payload = data["payload"]
            market_cache[cache_key] = payload
            return payload
        return None

    # ========================================================================
    # 物品 / Items
    # ========================================================================

    @classmethod
    async def get_items(cls) -> Optional[list[dict]]:
        """获取所有可交易物品列表。

        Returns:
            物品列表，每个包含 id, item_name, url_name, thumb 等字段。
        """
        payload = await cls._fetch_with_cache(
            f"{cls.BASE_URL}/items", "items"
        )
        return payload.get("items") if payload else None

    @classmethod
    async def get_item_orders(cls, url_name: str) -> Optional[dict]:
        """获取指定物品的订单数据。

        Args:
            url_name: 物品的 url_name（如 "rhino_prime_set"）。

        Returns:
            包含 orders, included 等字段的字典。
        """
        return await cls._fetch_with_cache(
            f"{cls.BASE_URL}/items/{url_name}/orders",
            f"orders_{url_name}",
        )

    # ========================================================================
    # 赤毒 / 信条 幻纹 & 武器
    # ========================================================================

    @classmethod
    async def get_lich_ephemeras(cls) -> Optional[list[dict]]:
        """获取赤毒幻纹列表。"""
        payload = await cls._fetch_with_cache(
            f"{cls.BASE_URL}/lich/ephemeras", "lich_ephemeras"
        )
        return payload.get("ephemeras") if payload else None

    @classmethod
    async def get_sister_ephemeras(cls) -> Optional[list[dict]]:
        """获取信条幻纹列表。"""
        payload = await cls._fetch_with_cache(
            f"{cls.BASE_URL}/sister/ephemeras", "sister_ephemeras"
        )
        return payload.get("ephemeras") if payload else None

    @classmethod
    async def get_lich_weapons(cls) -> Optional[list[dict]]:
        """获取赤毒武器列表。"""
        payload = await cls._fetch_with_cache(
            f"{cls.BASE_URL}/lich/weapons", "lich_weapons"
        )
        return payload.get("weapons") if payload else None

    @classmethod
    async def get_sister_weapons(cls) -> Optional[list[dict]]:
        """获取信条武器列表。"""
        payload = await cls._fetch_with_cache(
            f"{cls.BASE_URL}/sister/weapons", "sister_weapons"
        )
        return payload.get("weapons") if payload else None

    # ========================================================================
    # 紫卡 / Riven
    # ========================================================================

    @classmethod
    async def get_riven_weapons(cls) -> Optional[list[dict]]:
        """获取紫卡武器列表。"""
        payload = await cls._fetch_with_cache(
            f"{cls.BASE_URL}/riven/weapons", "riven_weapons"
        )
        return payload.get("weapons") if payload else None

    @classmethod
    async def search_auctions(
        cls,
        weapon_url_name: str,
        sort_by: str = "price_asc",
        page: int = 0,
    ) -> Optional[dict]:
        """搜索紫卡拍卖。

        Args:
            weapon_url_name: 武器 url_name。
            sort_by: 排序方式（price_asc, price_desc, etc.）。
            page: 页码。

        Returns:
            拍卖搜索结果。
        """
        cache_key = f"auction_{weapon_url_name}_{sort_by}_{page}"
        if cache_key in market_cache:
            return market_cache[cache_key]

        params = {
            "weapon_url_name": weapon_url_name,
            "sort_by": sort_by,
            "page": page,
        }
        param_str = "&".join(f"{k}={v}" for k, v in params.items())
        data = await fetch_json(
            f"{cls.AUCTIONS_URL}/search?{param_str}",
            headers={"Content-Type": "application/json"},
        )

        if data and "payload" in data:
            market_cache[cache_key] = data["payload"]
            return data["payload"]
        return None

    # ========================================================================
    # 搜索 / Search
    # ========================================================================

    @classmethod
    async def search_items(cls, query: str) -> Optional[list[dict]]:
        """搜索物品。

        Args:
            query: 搜索关键词。

        Returns:
            匹配的物品列表。
        """
        return await cls._fetch_with_cache(
            f"{cls.BASE_URL}/search/{query}", f"search_{query}"
        )
