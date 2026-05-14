"""CDN Data Source client / CDN 数据源客户端

封装从 CDN 获取 Warframe 配置数据（别名、节点等）的接口。
"""
from __future__ import annotations

import asyncio
from typing import Any, Optional

from astrbot.api import logger

from ..config import get_wf_data_source_cdn
from ..util import fetch_json

# 获取数据失败时的重试配置
_MAX_RETRIES = 3
# 每次重试间隔（秒）
_RETRY_DELAY = 5 


class DataSourceClient:
    """CDN 数据源客户端。

    用于从 CDN 获取 Warframe 辅助数据，如别名映射、星图节点等。
    """

    @classmethod
    def _base_url(cls) -> str:
        """获取当前配置的 CDN 基础 URL。"""
        return get_wf_data_source_cdn()

    @classmethod
    async def _fetch_with_retry(cls, url: str, name: str) -> Optional[Any]:
        """获取 JSON 数据，失败时自动重试（内部方法，外部不应调用）。

        Args:
            url: 请求 URL。
            name: 数据名称（用于日志）。

        Returns:
            解析后的 JSON 数据，重试超限后返回 None。
        """
        for attempt in range(1, _MAX_RETRIES + 1):
            data = await fetch_json(url)
            if data is not None:
                return data
            if attempt < _MAX_RETRIES:
                logger.warning(
                    f"获取 {name} 数据失败（第 {attempt}/{_MAX_RETRIES} 次），"
                    f"{_RETRY_DELAY} 秒后重试..."
                )
                await asyncio.sleep(_RETRY_DELAY)
        logger.error(f"获取 {name} 数据失败，已重试 {_MAX_RETRIES} 次，放弃")
        return None

    @classmethod
    async def fetch_alias(cls) -> Optional[list[dict]]:
        """获取别名数据。

        Returns:
            别名列表 [{"cn": "中文名", "en": "English Name"}, ...]。
        """
        url = f"{cls._base_url()}/warframe/alias.json"
        return await cls._fetch_with_retry(url, "别名")

    @classmethod
    async def fetch_nodes(cls) -> Optional[list[dict]]:
        """获取星图节点数据。

        Returns:
            节点列表。
        """
        url = f"{cls._base_url()}/warframe/nodes.json"
        return await cls._fetch_with_retry(url, "星图节点")

    @classmethod
    async def fetch_state_translations(cls) -> Optional[dict]:
        """获取翻译数据。
        
        Returns:
            Lost路径翻译
        """
        url = f"{cls._base_url()}/warframe/state_translation.json"
        return await cls._fetch_with_retry(url, "翻译")

    @classmethod
    async def fetch_rive_tion(cls) -> Optional[list[dict]]:
        """获取Riven Tion 紫卡属性查询参数"""
        url = f"{cls._base_url}/warframe/market_riven_tion.json"
        return await cls._fetch_with_retry(url, "紫卡属性查询参数")
    
    @classmethod
    async def fetch_riven_tion_alias(cls) -> Optional[list[dict]]:
        """获取Riven Tion Alias 紫卡属性查询别名"""
        url = f"{cls._base_url}/warframe/market_riven_tion_alias.json"
        return await cls._fetch_with_retry(url, "紫卡属性查询别名")

    @classmethod
    async def fetch_reward_pool(cls) -> Optional[list[dict]]:
        """获取 奖励池 数据"""
        url = f"{cls._base_url}/warframe/reward_pool.json"
        return await cls._fetch_with_retry(url, "奖励池")
    
    @classmethod
    async def fethc_riven_analyse_trend(cls) -> Optional[list[dict]]:
        """获取 紫卡计算器 数据"""
        url = f"{cls._base_url}/warframe/riven_analyse_trend.json"
        return await cls._fetch_with_retry(url, "紫卡计算器")