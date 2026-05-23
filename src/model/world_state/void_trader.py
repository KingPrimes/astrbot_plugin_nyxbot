"""
VoidTrader Model / 虚空商人模型

对应 Java: VoidTrader.java
继承 BastWorldState，包含 Character、Node、Manifest（商品清单嵌套类）。
"""
from __future__ import annotations

from pydantic import Field

from .base import BaseModelWithAlias, BastWorldState


class VoidTrader(BastWorldState):
    """虚空商人 / Void Trader (Baro Ki'Teer)

    对应 Java: VoidTrader extends BastWorldState
    """

    class Manifest(BaseModelWithAlias):
        """虚空商人商品清单 / Void Trader Manifest Item

        Java: VoidTrader.Manifest
        """
        item: str | None = Field(default=None, alias="ItemType")
        prime_price: int | None = Field(default=None, alias="PrimePrice")
        regular_price: int | None = Field(default=None, alias="RegularPrice")
        limit: int | None = Field(default=None, alias="Limit")
    character: str | None = Field(default=None, alias="Character")
    node: str | None = Field(default=None, alias="Node")
    manifest: list[Manifest] = Field(default_factory=list, alias="Manifest")

