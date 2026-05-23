"""
DailyDeals Model / 每日特惠模型

对应 Java: DailyDeals.java
继承 BastWorldState，包含折扣、售价、原价、商品名、已售/总数。
"""
from __future__ import annotations

from pydantic import Field

from .base import BastWorldState


class DailyDeals(BastWorldState):
    """每日特惠 / Daily Deals

    对应 Java: DailyDeals extends BastWorldState
    """

    sold: int | None = Field(default=None, alias="AmountSold")
    total: int | None = Field(default=None, alias="AmountTotal")
    discount: float | None = Field(default=None, alias="Discount")
    original_price: int | None = Field(default=None, alias="OriginalPrice")
    sale_price: int | None = Field(default=None, alias="SalePrice")
    item: str | None = Field(default=None, alias="StoreItem")

