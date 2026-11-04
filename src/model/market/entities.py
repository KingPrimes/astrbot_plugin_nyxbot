"""Market entity models / 市场实体模型

按 <https://docs.warframe.market/docs/data-models>（API v0.25.0）定义的响应模型：
``Item`` / ``RivenWeapon`` / ``LichWeapon`` / ``Ephemera``。

这些模型只负责**接收与校验**，落库由 ``service/*_sync`` 转成 Tortoise 行。
字段名与文档一致（camelCase），通过 alias 映射到 Python 的 snake_case。
"""
from __future__ import annotations

from pydantic import Field

from ..base import BaseModelWithAlias


class ItemI18N(BaseModelWithAlias):
    """Item.i18n 的单语言条目。"""

    name: str | None = Field(default=None)
    description: str | None = Field(default=None)
    wiki_link: str | None = Field(default=None, alias="wikiLink")
    icon: str | None = Field(default=None)
    thumb: str | None = Field(default=None)
    sub_icon: str | None = Field(default=None, alias="subIcon")


class Item(BaseModelWithAlias):
    """物品（/v2/items 与 /v2/item/{slug}/set 的并集）。"""

    id: str
    slug: str | None = Field(default=None)
    game_ref: str | None = Field(default=None, alias="gameRef")
    tags: list[str] = Field(default_factory=list)
    set_root: bool | None = Field(default=None, alias="setRoot")
    set_parts: list[str] = Field(default_factory=list, alias="setParts")
    quantity_in_set: int | None = Field(default=None, alias="quantityInSet")
    rarity: str | None = Field(default=None)
    bulk_tradable: bool | None = Field(default=None, alias="bulkTradable")
    subtypes: list[str] = Field(default_factory=list)
    max_rank: int | None = Field(default=None, alias="maxRank")
    max_charges: int | None = Field(default=None, alias="maxCharges")
    max_amber_stars: int | None = Field(default=None, alias="maxAmberStars")
    max_cyan_stars: int | None = Field(default=None, alias="maxCyanStars")
    base_endo: int | None = Field(default=None, alias="baseEndo")
    endo_multiplier: float | None = Field(default=None, alias="endoMultiplier")
    ducats: int | None = Field(default=None)
    vosfor: int | None = Field(default=None)
    req_mastery_rank: int | None = Field(default=None, alias="reqMasteryRank")
    vaulted: bool | None = Field(default=None)
    trading_tax: int | None = Field(default=None, alias="tradingTax")
    tradable: bool | None = Field(default=None)
    i18n: dict[str, ItemI18N] = Field(default_factory=dict)


class RivenWeaponI18N(BaseModelWithAlias):
    """RivenWeapon.i18n 的单语言条目。"""

    name: str | None = Field(default=None)
    wiki_link: str | None = Field(default=None, alias="wikiLink")
    icon: str | None = Field(default=None)
    thumb: str | None = Field(default=None)
    sub_icon: str | None = Field(default=None, alias="subIcon")


class RivenWeapon(BaseModelWithAlias):
    """裂罅武器（/v2/rivens/weapons）。"""

    id: str
    slug: str | None = Field(default=None)
    game_ref: str | None = Field(default=None, alias="gameRef")
    group: str | None = Field(default=None)
    riven_type: str | None = Field(default=None, alias="rivenType")
    disposition: float | None = Field(default=None)
    req_mastery_rank: int | None = Field(default=None, alias="reqMasteryRank")
    i18n: dict[str, RivenWeaponI18N] = Field(default_factory=dict)


class LichWeaponI18N(BaseModelWithAlias):
    """LichWeapon.i18n 的单语言条目。"""

    name: str | None = Field(default=None)
    wiki_link: str | None = Field(default=None, alias="wikiLink")
    icon: str | None = Field(default=None)
    thumb: str | None = Field(default=None)


class LichWeapon(BaseModelWithAlias):
    """玄骸武器（/v2/liches/weapons 与 /v2/sisters/weapons 共用）。"""

    id: str
    slug: str | None = Field(default=None)
    game_ref: str | None = Field(default=None, alias="gameRef")
    req_mastery_rank: int | None = Field(default=None, alias="reqMasteryRank")
    i18n: dict[str, LichWeaponI18N] = Field(default_factory=dict)


class EphemeraI18N(BaseModelWithAlias):
    """Ephemera.i18n 的单语言条目。"""

    name: str | None = Field(default=None)
    icon: str | None = Field(default=None)
    thumb: str | None = Field(default=None)


class Ephemera(BaseModelWithAlias):
    """玄骸幻纹（/v2/liches/ephemeras 与 /v2/sisters/ephemeras 共用）。"""

    id: str
    slug: str | None = Field(default=None)
    game_ref: str | None = Field(default=None, alias="gameRef")
    animation: str | None = Field(default=None)
    element: str | None = Field(default=None)
    i18n: dict[str, EphemeraI18N] = Field(default_factory=dict)
