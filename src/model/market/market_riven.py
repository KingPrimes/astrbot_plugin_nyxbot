"""Market Riven model / 紫卡市场数据模型

对应 Java MarketRiven.java — API v1 版本
"""
from __future__ import annotations

from pydantic import Field, field_validator

from ...wenum.polarity import PolarityEnum
from ..base import BaseModelWithAlias
from .base import BaseAuction, MarketOwner
from .whisper import WhisperEntry


class RivenAttribute(BaseModelWithAlias):
    """紫卡词条 — 对应 Java MarketRiven.Attributes"""
    value: float | None = Field(default=None)
    positive: bool | None = Field(default=None)
    url_name: str | None = Field(default=None, alias="url_name")



class RivenItem(BaseModelWithAlias):
    """紫卡物品 — 对应 Java MarketRiven.Item"""
    type: str | None = Field(default=None)
    mod_rank: int | None = Field(default=None, alias="mod_rank")
    weapon_url_name: str | None = Field(default=None, alias="weapon_url_name")
    attributes: list[RivenAttribute] = Field(default_factory=list)
    name: str | None = Field(default=None)
    re_rolls: int | None = Field(default=None, alias="re_rolls")
    polarity: PolarityEnum | None = Field(default=None)
    mastery_level: int | None = Field(default=None, alias="mastery_level")


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


class RivenOwner(MarketOwner):
    """卖家信息 — 继承 MarketOwner 共享基类（无额外字段）。"""


class RivenAuction(BaseAuction[RivenItem, RivenOwner]):
    """紫卡拍卖 — 继承 BaseAuction 共享基类（无额外字段）。"""



class MarketRivenPayload(BaseModelWithAlias):
    """紫卡载荷 — 对应 Java MarketRiven.Payload"""
    auctions: list[RivenAuction] = Field(default_factory=list)



class MarketRiven(BaseModelWithAlias):
    """紫卡市场数据 — 对应 Java MarketRiven"""
    item_name: str = Field(default="", alias="item_name")
    payload: MarketRivenPayload | None = Field(default=None)
    whispers: list[WhisperEntry] = Field(default_factory=list)
    """与 payload.auctions 一一对应的私聊语句。"""
