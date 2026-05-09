"""CDN Data Source client / CDN 数据源客户端

封装从 CDN 获取 Warframe 配置数据（别名、节点等）的接口。
"""
from __future__ import annotations

from typing import Any, Optional

from ..config import get_wf_data_source_cdn
from ..util import fetch_json


class DataSourceClient:
    """CDN 数据源客户端。

    用于从 CDN 获取 Warframe 辅助数据，如别名映射、星图节点等。
    """

    @classmethod
    def _base_url(cls) -> str:
        """获取当前配置的 CDN 基础 URL。"""
        return get_wf_data_source_cdn()

    @classmethod
    async def fetch_alias(cls) -> Optional[list[dict]]:
        """获取别名数据。

        Returns:
            别名列表 [{"cn": "中文名", "en": "English Name"}, ...]。
        """
        return await fetch_json(f"{cls._base_url()}/warframe/alias.json")

    @classmethod
    async def fetch_nodes(cls) -> Optional[list[dict]]:
        """获取星图节点数据。

        Returns:
            节点列表。
        """
        return await fetch_json(f"{cls._base_url()}/warframe/nodes.json")

    @classmethod
    async def fetch_translations(cls) -> Optional[dict]:
        """获取翻译数据。"""
        return await fetch_json(f"{cls._base_url()}/warframe/translation.json")

    @classmethod
    async def fetch_relics(cls) -> Optional[list[dict]]:
        """获取遗物数据。"""
        return await fetch_json(f"{cls._base_url()}/warframe/relics.json")
