"""Market service / 市场服务

封装 Warframe.Market 的业务逻辑。
"""
from __future__ import annotations

from typing import Any, Optional

from ..api import MarketClient
from ..util import market_cache


class MarketService:
    """市场数据服务。"""

    @classmethod
    async def search_items(cls, query: str) -> Optional[list[dict]]:
        """搜索物品。

        Args:
            query: 搜索关键词。

        Returns:
            匹配的物品列表。
        """
        return await MarketClient.search_items(query)

    @classmethod
    async def get_item_orders(cls, url_name: str) -> Optional[dict]:
        """获取指定物品的订单。

        Args:
            url_name: 物品的 url_name。

        Returns:
            包含订单数据的字典。
        """
        return await MarketClient.get_item_orders(url_name)

    @classmethod
    async def get_lich_weapons(cls) -> Optional[list[dict]]:
        """获取赤毒武器列表。"""
        return await MarketClient.get_lich_weapons()

    @classmethod
    async def get_sister_weapons(cls) -> Optional[list[dict]]:
        """获取信条武器列表。"""
        return await MarketClient.get_sister_weapons()

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
            sort_by: 排序方式。
            page: 页码。

        Returns:
            拍卖搜索结果。
        """
        return await MarketClient.search_auctions(weapon_url_name, sort_by, page)

    @classmethod
    def clear_cache(cls) -> None:
        """清除市场数据缓存。"""
        market_cache.clear()
