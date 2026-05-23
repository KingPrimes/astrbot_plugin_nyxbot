"""
FeaturedGuilds Model / 精选氏族模型

对应 Java: FeaturedGuilds.java
继承 BastWorldState，包含 AllianceId、Emblem、HiddenPlatforms（嵌套）、Name、Tier 等。
"""
from __future__ import annotations

from pydantic import Field

from .base import BaseModelWithAlias, BastWorldState, Id


class FeaturedGuilds(BastWorldState):
    """精选氏族 / Featured Guilds

    对应 Java: FeaturedGuilds extends BastWorldState
    """

    class HiddenPlatforms(BaseModelWithAlias):
        """隐藏平台信息 / Hidden Platforms

        Java: FeaturedGuilds.HiddenPlatforms
        """
        ios: bool = Field(default=False, alias="PLATFORM_IOS")
        switch_platform: bool = Field(default=False, alias="PLATFORM_SWITCH")
        cross_platform: bool = Field(default=False, alias="PLATFORM_CROSS_PLATFORM")
    id: Id | None = Field(default=None, alias="AllianceId")
    emblem: bool | None = Field(default=None, alias="Emblem")
    hidden_platforms: HiddenPlatforms | None = Field(default=None, alias="HiddenPlatforms")
    icon_override: int | None = Field(default=None, alias="IconOverride")
    name: str | None = Field(default=None, alias="Name")
    tier: int | None = Field(default=None, alias="Tier")

