"""Market model shared base classes / Market 模型共享基类

消除 RivenOwner/LichSisterOwner 和 RivenAuction/LichSisterAuction 的字段重复。
"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import Field

from ..base import BaseModelWithAlias

T_Item = TypeVar("T_Item")
T_Owner = TypeVar("T_Owner")


class MarketOwner(BaseModelWithAlias):
    """卖家信息基类 — 原 RivenOwner / LichSisterOwner 完全相同的 8 个字段。"""

    reputation: int | None = Field(default=None)
    locale: str | None = Field(default=None)
    avatar: str | None = Field(default=None)
    last_seen: str | None = Field(default=None, alias="last_seen")
    ingame_name: str | None = Field(default=None, alias="ingame_name")
    slug: str | None = Field(default=None)
    status: str | None = Field(default=None)
    platform: str | None = Field(default=None)
    crossplay: bool | None = Field(default=None)
    id: str | None = Field(default=None)
    region: str | None = Field(default=None)


class BaseAuction(BaseModelWithAlias, Generic[T_Item, T_Owner]):
    """拍卖基类 — 原 RivenAuction / LichSisterAuction 的 11 个公共字段。

    仅 item 类型（T_Item）和 owner 类型（T_Owner）因场景不同而泛型化。
    """

    buyout_price: int | None = Field(default=None, alias="buyout_price")
    note: str | None = Field(default=None)
    visible: bool | None = Field(default=None)
    item: T_Item | None = Field(default=None)
    starting_price: int | None = Field(default=None, alias="starting_price")
    minimal_reputation: int | None = Field(default=None, alias="minimal_reputation")
    owner: T_Owner | None = Field(default=None)
    platform: str | None = Field(default=None)
    closed: bool | None = Field(default=None)
    top_bid: int | None = Field(default=None, alias="top_bid")
    created: str | None = Field(default=None)
    updated: str | None = Field(default=None)
    is_direct_sell: bool | None = Field(default=None, alias="is_direct_sell")
    id: str | None = Field(default=None)
    crossplay: bool | None = Field(default=None)
    private: bool | None = Field(default=None)
    note_raw: str | None = Field(default=None, alias="note_raw")
    is_marked_for: str | None = Field(default=None, alias="is_marked_for")
    marked_operation_at: str | None = Field(default=None, alias="marked_operation_at")
    winner: Any | None = Field(default=None)
