"""
FlashSale Model / 闪购商品模型

对应 Java: FlashSale.java
不继承 BastWorldState（Java 源中无 extends），包含 BogoBuy/BogoGet、折扣、时间、价格覆盖等。
"""
from __future__ import annotations

from pydantic import Field

from .base import BaseModelWithAlias, DateField


class FlashSale(BaseModelWithAlias):
    """闪购商品 / Flash Sale

    对应 Java: FlashSale（不继承 BastWorldState）
    """

    bogo_buy: int | None = Field(default=None, alias="BogoBuy")
    bogo_get: int | None = Field(default=None, alias="BogoGet")
    daily_sale_generated: bool | None = Field(default=None, alias="DailySaleGenerated")
    discount: int | None = Field(default=None, alias="Discount")
    end_date: DateField | None = Field(default=None, alias="EndDate")
    hide_from_market: bool | None = Field(default=None, alias="HideFromMarket")
    premium_override: int | None = Field(default=None, alias="PremiumOverride")
    regular_override: int | None = Field(default=None, alias="RegularOverride")
    show_in_market: bool | None = Field(default=None, alias="ShowInMarket")
    start_date: DateField | None = Field(default=None, alias="StartDate")
    supporter_pack: bool | None = Field(default=None, alias="SupporterPack")
    type_name: str | None = Field(default=None, alias="TypeName")

