"""
PrimeVaultTrader Model / 瓦奇娅火星集市模型

对应 Java: PrimeVaultTrader.java
继承 BastWorldState，包含 InitialStartDate、Node、Manifest、EvergreenManifest、ScheduleInfo。
"""
from __future__ import annotations

from pydantic import Field

from .base import BastWorldState, DateField
from .manifest_item import ManifestItem
from .schedule_info import ScheduleInfo


class PrimeVaultTrader(BastWorldState):
    """瓦奇娅火星集市 / Prime Vault Trader (Varzia)

    对应 Java: PrimeVaultTrader extends BastWorldState
    """

    initial_start_date: DateField | None = Field(default=None, alias="InitialStartDate")
    node: str | None = Field(default=None, alias="Node")
    manifest: list[ManifestItem] = Field(default_factory=list, alias="Manifest")
    evergreen_manifest: list[ManifestItem] = Field(default_factory=list, alias="EvergreenManifest")
    schedule_infos: list[ScheduleInfo] = Field(default_factory=list, alias="ScheduleInfo")

