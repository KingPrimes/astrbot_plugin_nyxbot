"""
ManifestItem Model / 瓦奇娅商品清单模型

对应 Java: ManifestItem.java
不继承 BastWorldState，包含 ItemType、PrimePrice、RegularPrice。
用于 PrimeVaultTrader.manifest 和 PrimeVaultTrader.evergreen_manifest。
"""
from __future__ import annotations

from pydantic import Field

from .base import BaseModelWithAlias


class ManifestItem(BaseModelWithAlias):
    """瓦奇娅商品清单 / Prime Vault Manifest Item

    对应 Java: ManifestItem
    """

    item_type: str | None = Field(default=None, alias="ItemType")
    prime_price: int | None = Field(default=None, alias="PrimePrice")
    regular_price: int | None = Field(default=None, alias="RegularPrice")

