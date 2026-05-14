"""Translation service / 翻译服务

提供 Warframe 物品名称的中英文翻译查询（基于 Alias 表）
以及状态翻译查询（基于 StateTranslation 表）。
"""
from __future__ import annotations

from typing import Optional


class TranslationService:
    """翻译服务：中英文名称互查 + 状态翻译。"""

    # ── Alias 翻译 ────────────────────────────────────────────────────

    @classmethod
    async def cn_to_en(cls, cn_name: str) -> Optional[str]:
        """中文名 → 英文名。

        Args:
            cn_name: 中文名称。

        Returns:
            英文名称，未找到返回 None。
        """
        ...

    @classmethod
    async def en_to_cn(cls, en_name: str) -> Optional[str]:
        """英文名 → 中文名。

        Args:
            en_name: 英文名称。

        Returns:
            中文名称，未找到返回 None。
        """
        ...

    @classmethod
    async def search(cls, keyword: str, page: int = 1, page_size: int = 20):
        """模糊搜索中英文别名。

        Returns:
            (结果列表, 总数) 的元组。
        """
        ...

    # ── StateTranslation 翻译 ─────────────────────────────────────────

    @classmethod
    async def get_state_translation(
        cls, unique_name: str
    ) -> Optional[str]:
        """根据唯一名称获取状态翻译名称。

        Args:
            unique_name: 唯一名称。

        Returns:
            翻译后的名称，未找到返回 None。
        """
        ...

    @classmethod
    async def search_state(
        cls, keyword: str, page: int = 1, page_size: int = 20
    ):
        """模糊搜索状态翻译。

        Returns:
            (结果列表, 总数) 的元组。
        """
        ...
