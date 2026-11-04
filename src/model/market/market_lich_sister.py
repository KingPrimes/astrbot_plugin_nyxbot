"""Market Lich/Sister model / 赤毒/信条拍卖数据模型

对应 Java MarketLichSister.java — API v1 版本
"""
from __future__ import annotations

from pydantic import Field

from ..base import BaseModelWithAlias
from .base import BaseAuction, MarketOwner
from .whisper import WhisperEntry


class LichSisterItem(BaseModelWithAlias):
    """拍卖物品 — 对应 Java MarketLichSister.Item"""
    type: str | None = Field(default=None)
    damage: int | None = Field(default=None)
    weapon_url_name: str | None = Field(default=None, alias="weapon_url_name")
    having_ephemera: bool | None = Field(default=None, alias="having_ephemera")
    element: str | None = Field(default=None)



class LichSisterOwner(MarketOwner):
    """卖家信息 — 继承 MarketOwner 共享基类（无额外字段）。"""


class LichSisterAuction(BaseAuction[LichSisterItem, LichSisterOwner]):
    """拍卖项目 — 继承 BaseAuction 共享基类（无额外字段）。"""



class MarketLichSisterPayload(BaseModelWithAlias):
    """载荷 — 对应 Java MarketLichSister.Payload"""
    auctions: list[LichSisterAuction] = Field(default_factory=list)
    item_name: str = Field(default="", alias="item_name")



class MarketLichSister(BaseModelWithAlias):
    """赤毒/信条拍卖数据 — 对应 Java MarketLichSister"""
    payload: MarketLichSisterPayload | None = Field(default=None)
    whispers: list[WhisperEntry] = Field(default_factory=list)
    """与 payload.auctions 一一对应的私聊语句。"""
