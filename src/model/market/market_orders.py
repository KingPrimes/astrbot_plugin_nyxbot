"""Market Orders model / 市场订单数据模型

对应 Java:
  - Orders.java (图片渲染用)
  - OrderWithUser.java (订单+用户)
  - MarketUser.java (用户信息)
  - BaseOrder.java (API v2 响应基类)
"""
from __future__ import annotations

from enum import StrEnum, unique

from pydantic import Field

from ..base import BaseModelWithAlias


@unique
class MarketStatusEnum(StrEnum):
    """用户在线状态 — 对应 Java MarketStatusEnum"""
    ONLINE = "online"
    INGAME = "ingame"
    OFFLINE = "offline"
    INVISIBLE = "invisible"


@unique
class ActivityTypeEnum(StrEnum):
    """用户活动类型 — 对应文档 ActivityType"""
    UNKNOWN = "UNKNOWN"
    IDLE = "IDLE"
    ON_MISSION = "ON_MISSION"
    IN_DOJO = "IN_DOJO"
    IN_ORBITER = "IN_ORBITER"
    IN_RELAY = "IN_RELAY"


class Activity(BaseModelWithAlias):
    """用户当前活动 — 对应文档 Activity"""
    type: str | None = Field(default=None)
    details: str | None = Field(default=None)
    started_at: str | None = Field(default=None, alias="startedAt")


@unique
class TransactionEnum(StrEnum):
    """交易类型 — 对应 Java TransactionEnum"""
    BUY = "buy"
    SELL = "sell"


@unique
class MarketPlatformEnum(StrEnum):
    """平台 — 对应 Java MarketPlatformEnum"""
    PC = "pc"
    PS4 = "ps4"
    XBOX = "xbox"
    SWITCH = "switch"
    MOBILE = "mobile"


class MarketUser(BaseModelWithAlias):
    """Market 用户信息 — 对应 Java MarketUser"""
    id: str | None = Field(default=None)
    ingame_name: str | None = Field(default=None, alias="ingameName")
    slug: str | None = Field(default=None)
    avatar: str | None = Field(default=None)
    reputation: int | None = Field(default=None)
    locale: str | None = Field(default=None)
    platform: MarketPlatformEnum | None = Field(default=None)
    crossplay: bool | None = Field(default=None)
    status: MarketStatusEnum | None = Field(default=None)
    activity: Activity | None = Field(default=None)
    last_seen: str | None = Field(default=None, alias="lastSeen")


class OrderWithUser(BaseModelWithAlias):
    """订单 + 用户信息 — 对应 Java OrderWithUser"""
    id: str | None = Field(default=None)
    type: TransactionEnum | None = Field(default=None)
    platinum: int | None = Field(default=None)
    quantity: int | None = Field(default=None)
    per_trade: int | None = Field(default=None, alias="perTrade")
    rank: int | None = Field(default=None)
    charges: int | None = Field(default=None)
    subtype: str | None = Field(default=None)
    amber_stars: int | None = Field(default=None, alias="amberStars")
    cyan_stars: int | None = Field(default=None, alias="cyanStars")
    visible: bool | None = Field(default=None)
    created_at: str | None = Field(default=None, alias="createdAt")
    updated_at: str | None = Field(default=None, alias="updatedAt")
    item_id: str | None = Field(default=None, alias="itemId")
    group_id: str | None = Field(default=None, alias="groupId")
    user: MarketUser | None = Field(default=None)


class Orders(BaseModelWithAlias):
    """市场订单渲染数据 — 对应 Java Orders"""
    name: str = Field(default="")
    form: str = Field(default="pc")
    is_by: bool = Field(default=False)  # True=购买, False=出售
    is_max: bool = Field(default=False)
    ducats: int = Field(default=0)
    vaulted: bool = Field(default=False)
    max_amber_stars: int = Field(default=0, alias="maxAmberStars")
    max_cyan_stars: int = Field(default=0, alias="maxCyanStars")
    base_endo: int = Field(default=0, alias="baseEndo")
    req_mastery_rank: int = Field(default=0, alias="reqMasteryRank")
    trading_tax: int = Field(default=0, alias="tradingTax")
    orders: list[OrderWithUser] = Field(default_factory=list)
