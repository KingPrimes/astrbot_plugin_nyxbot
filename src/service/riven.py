"""Riven service / 紫卡分析服务

提供紫卡趋势分析和属性计算功能。
"""
from __future__ import annotations

from typing import Any, Optional


class RivenAttributeCalculator:
    """紫卡属性计算器（参考 Java RivenAnalyseTrendCompute）。"""

    @staticmethod
    def calculate_disposition(base_value: float, riven_disposition: float) -> float:
        """计算紫卡倾向系数。

        Args:
            base_value: 基础属性值。
            riven_disposition: 紫卡倾向。

        Returns:
            调整后的属性值。
        """
        return base_value * riven_disposition

    @staticmethod
    def estimate_price(riven_data: dict) -> float:
        """估算紫卡价格。

        Args:
            riven_data: 紫卡数据字典，包含属性、倾向等信息。

        Returns:
            估算价格（白金）。
        """
        # 基础实现：根据属性数量和数值估算
        attributes = riven_data.get("attributes", [])
        reroll_count = riven_data.get("reroll_count", 0)
        mastery_rank = riven_data.get("mastery_rank", 0)

        base_price = 50.0
        # 属性加成
        attr_count = len(attributes)
        if attr_count >= 3:
            base_price *= 2.0
        if attr_count >= 4:
            base_price *= 1.5

        # 洗牌次数影响（洗得越多通常越贵）
        if reroll_count > 10:
            base_price *= 1.3
        elif reroll_count > 5:
            base_price *= 1.15

        # 段位要求
        if mastery_rank > 12:
            base_price *= 1.1

        return round(base_price, 1)


class RivenService:
    """紫卡分析服务。"""

    @classmethod
    async def get_weapon_list(cls) -> Optional[list[dict]]:
        """获取紫卡武器列表。"""
        from ..api import MarketClient

        return await MarketClient.get_riven_weapons()

    @classmethod
    async def search_auctions(
        cls,
        weapon_url_name: str,
        sort_by: str = "price_asc",
        page: int = 0,
    ) -> Optional[dict]:
        """搜索紫卡拍卖。"""
        from ..api import MarketClient

        return await MarketClient.search_auctions(weapon_url_name, sort_by, page)
