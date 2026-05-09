"""Market model package / Warframe.Market 响应模型包"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class MarketItem(BaseModel):
    """市场物品"""
    id: str = ""
    item_name: str = Field(default="", alias="item_name")
    url_name: str = Field(default="", alias="url_name")
    thumb: str = ""
    ducats: int = 0


class Order(BaseModel):
    """市场订单"""
    id: str = ""
    platinum: int = 0
    quantity: int = 0
    order_type: str = Field(default="sell", alias="order_type")
    user_status: str = Field(default="", alias="user_status")
    platform: str = "pc"


class RivenAuction(BaseModel):
    """紫卡拍卖"""
    id: str = ""
    weapon_url_name: str = Field(default="", alias="weapon_url_name")
    platinum: int = 0
    buyout_price: int = Field(default=0, alias="buyout_price")
    starting_price: int = Field(default=0, alias="starting_price")
    top_bid: int = Field(default=0, alias="top_bid")


class LichWeapon(BaseModel):
    """赤毒/信条武器"""
    id: str = ""
    item_name: str = Field(default="", alias="item_name")
    url_name: str = Field(default="", alias="url_name")
    element: str = ""


class Ephemera(BaseModel):
    """幻纹"""
    id: str = ""
    item_name: str = Field(default="", alias="item_name")
    url_name: str = Field(default="", alias="url_name")


__all__ = [
    "MarketItem",
    "Order",
    "RivenAuction",
    "LichWeapon",
    "Ephemera",
]
