"""
InGameMarket Model / 游戏内商城模型

对应 Java: InGameMarket.java
不继承 BastWorldState，包含 LandingPage（嵌套类）、Category（嵌套类）、CategoryName（枚举）。

CategoryName 枚举成员: NEW_PLAYER, NEW, COMMUNITY, HEIRLOOM, TENNOGEN, SALE,
WISH_LIST, PREMIUM_BUNDLES, POPULAR, SEASONAL
"""
from __future__ import annotations

from enum import Enum

from pydantic import Field

from .base import BaseModelWithAlias


class CategoryName(Enum):
    """商城分类枚举 / Market Category Enum

    对应 Java: InGameMarket.CategoryName
    """
    NEW_PLAYER = "NEW_PLAYER"
    NEW = "NEW"
    COMMUNITY = "COMMUNITY"
    HEIRLOOM = "HEIRLOOM"
    TENNOGEN = "TENNOGEN"
    SALE = "SALE"
    WISH_LIST = "WISH_LIST"
    PREMIUM_BUNDLES = "PREMIUM_BUNDLES"
    POPULAR = "POPULAR"
    SEASONAL = "SEASONAL"
    QUICK_BUY = "QUICK_BUY"

    @classmethod
    def _missing_(cls, value):
        """未知分类名回退到 POPULAR。"""
        if isinstance(value, str):
            try:
                return cls[value]
            except KeyError:
                pass
        return cls.POPULAR


class InGameMarket(BaseModelWithAlias):
    """游戏内商城 / In-Game Market

    对应 Java: InGameMarket
    """

    class Category(BaseModelWithAlias):
        """商城分类 / Market Category

        Java: InGameMarket.Category
        """
        category_name: CategoryName | None = Field(default=None, alias="CategoryName")
        name: str | None = Field(default=None, alias="Name")
        icon: str | None = Field(default=None, alias="Icon")
        add_to_menu: bool | None = Field(default=None, alias="AddToMenu")
        items: list[str] = Field(default_factory=list, alias="Items")
    class LandingPage(BaseModelWithAlias):
        """商城首页 / Landing Page

        Java: InGameMarket.LandingPage
        """
        categories: list[InGameMarket.Category] = Field(default_factory=list, alias="Categories")
    landing_page: LandingPage | None = Field(default=None, alias="LandingPage")

