"""Market Lich/Sister model / 赤毒/信条拍卖数据模型

对应 Java MarketLichSister.java — API v1 版本
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class LichSisterItem(BaseModel):
    """拍卖物品 — 对应 Java MarketLichSister.Item"""
    type: str | None = Field(default=None)
    damage: int | None = Field(default=None)
    weapon_url_name: str | None = Field(default=None, alias="weapon_url_name")
    having_ephemera: bool | None = Field(default=None, alias="having_ephemera")
    element: str | None = Field(default=None)

    model_config = {"populate_by_name": True}


class LichSisterOwner(BaseModel):
    """卖家信息 — 对应 Java Owner"""
    reputation: int | None = Field(default=None)
    locale: str | None = Field(default=None)
    avatar: str | None = Field(default=None)
    last_seen: str | None = Field(default=None, alias="last_seen")
    ingame_name: str | None = Field(default=None, alias="ingame_name")
    status: str | None = Field(default=None)
    id: str | None = Field(default=None)
    region: str | None = Field(default=None)

    model_config = {"populate_by_name": True}


class LichSisterAuction(BaseModel):
    """拍卖项目 — 对应 Java MarketLichSister.Auctions"""
    buyout_price: int | None = Field(default=None, alias="buyout_price")
    note: str | None = Field(default=None)
    visible: bool | None = Field(default=None)
    item: LichSisterItem | None = Field(default=None)
    starting_price: int | None = Field(default=None, alias="starting_price")
    minimal_reputation: int | None = Field(default=None, alias="minimal_reputation")
    owner: LichSisterOwner | None = Field(default=None)
    platform: str | None = Field(default=None)
    closed: bool | None = Field(default=None)
    top_bid: int | None = Field(default=None, alias="top_bid")
    created: str | None = Field(default=None)
    updated: str | None = Field(default=None)
    is_direct_sell: bool | None = Field(default=None, alias="is_direct_sell")
    id: str | None = Field(default=None)

    model_config = {"populate_by_name": True}


class MarketLichSisterPayload(BaseModel):
    """载荷 — 对应 Java MarketLichSister.Payload"""
    auctions: list[LichSisterAuction] = Field(default_factory=list)
    item_name: str = Field(default="", alias="item_name")

    model_config = {"populate_by_name": True}


class MarketLichSister(BaseModel):
    """赤毒/信条拍卖数据 — 对应 Java MarketLichSister"""
    payload: MarketLichSisterPayload | None = Field(default=None)

    model_config = {"populate_by_name": True}
