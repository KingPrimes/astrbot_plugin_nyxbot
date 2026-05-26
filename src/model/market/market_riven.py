"""Market Riven model / 紫卡市场数据模型

对应 Java MarketRiven.java — API v1 版本
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from ...wenum.polarity import PolarityEnum


class RivenAttribute(BaseModel):
    """紫卡词条 — 对应 Java MarketRiven.Attributes"""
    value: float | None = Field(default=None)
    positive: bool | None = Field(default=None)
    url_name: str | None = Field(default=None, alias="url_name")

    model_config = {"populate_by_name": True}


class RivenItem(BaseModel):
    """紫卡物品 — 对应 Java MarketRiven.Item"""
    type: str | None = Field(default=None)
    mod_rank: int | None = Field(default=None, alias="mod_rank")
    weapon_url_name: str | None = Field(default=None, alias="weapon_url_name")
    attributes: list[RivenAttribute] = Field(default_factory=list)
    name: str | None = Field(default=None)
    re_rolls: int | None = Field(default=None, alias="re_rolls")
    polarity: PolarityEnum | None = Field(default=None)
    mastery_level: int | None = Field(default=None, alias="mastery_level")

    model_config = {"populate_by_name": True}

    @field_validator("polarity", mode="before")
    @classmethod
    def _normalize_polarity(cls, v: object) -> PolarityEnum | None:
        """API 返回的 polarity 是小写字符串（madurai/vazarin/...），
        而 PolarityEnum 的 value 是大写，需要先归一化。
        Normalize the lowercase polarity string from the API to PolarityEnum.
        """
        if v is None or isinstance(v, PolarityEnum):
            return v if isinstance(v, PolarityEnum) else None
        if isinstance(v, str):
            try:
                return PolarityEnum[v.upper()]
            except KeyError:
                return None
        return None


class RivenOwner(BaseModel):
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


class RivenAuction(BaseModel):
    """紫卡拍卖 — 对应 Java MarketRiven.Auctions"""
    buyout_price: int | None = Field(default=None, alias="buyout_price")
    note: str | None = Field(default=None)
    visible: bool | None = Field(default=None)
    item: RivenItem | None = Field(default=None)
    starting_price: int | None = Field(default=None, alias="starting_price")
    minimal_reputation: int | None = Field(default=None, alias="minimal_reputation")
    owner: RivenOwner | None = Field(default=None)
    platform: str | None = Field(default=None)
    closed: bool | None = Field(default=None)
    top_bid: int | None = Field(default=None, alias="top_bid")
    created: str | None = Field(default=None)
    updated: str | None = Field(default=None)
    is_direct_sell: bool | None = Field(default=None, alias="is_direct_sell")
    id: str | None = Field(default=None)

    model_config = {"populate_by_name": True}


class MarketRivenPayload(BaseModel):
    """紫卡载荷 — 对应 Java MarketRiven.Payload"""
    auctions: list[RivenAuction] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class MarketRiven(BaseModel):
    """紫卡市场数据 — 对应 Java MarketRiven"""
    item_name: str = Field(default="", alias="item_name")
    payload: MarketRivenPayload | None = Field(default=None)

    model_config = {"populate_by_name": True}
