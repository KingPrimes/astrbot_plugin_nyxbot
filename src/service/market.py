"""Market service / 市场服务

封装 Warframe.Market 的业务逻辑以及本地市场数据查询。
"""
from __future__ import annotations

from typing import Optional


class MarketService:
    """市场数据服务。"""

    # ── 远程 API ──────────────────────────────────────────────────────

    @classmethod
    async def search_items(cls, query: str) -> Optional[list[dict]]:
        """远程搜索物品。

        Args:
            query: 搜索关键词。

        Returns:
            匹配的物品列表。
        """
        ...

    @classmethod
    async def get_item_orders(cls, url_name: str) -> Optional[dict]:
        """获取指定物品的订单。

        Args:
            url_name: 物品的 url_name。

        Returns:
            包含订单数据的字典。
        """
        ...

    @classmethod
    async def get_lich_weapons(cls) -> Optional[list[dict]]:
        """获取赤毒武器列表（远程）。"""
        ...

    @classmethod
    async def get_sister_weapons(cls) -> Optional[list[dict]]:
        """获取信条武器列表（远程）。"""
        ...

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
        ...

    # ── 本地数据库 ────────────────────────────────────────────────────

    @classmethod
    async def get_local_orders_item(
        cls, slug: str
    ) -> Optional[dict]:
        """从本地 OrdersItems 表查询物品信息。

        Args:
            slug: URL slug。

        Returns:
            物品信息的字典（或 model_dump）。
        """
        ...

    @classmethod
    async def search_local_orders_items(
        cls, keyword: str, page: int = 1, page_size: int = 20
    ):
        """从本地 OrdersItems 表模糊搜索物品。

        Returns:
            (记录列表, 总数) 的元组。
        """
        ...

    # ── 缓存 ──────────────────────────────────────────────────────────

    @classmethod
    def clear_cache(cls) -> None:
        """清除市场数据缓存。"""
        ...
