"""CDN Data Source client / CDN 数据源客户端

封装从 CDN 获取 Warframe 配置数据（别名、节点等）的接口。
"""
from __future__ import annotations

from typing import Any, Optional

from ..config import get_wf_data_source_cdn
from ..util import fetch_json_with_retry, RetryLogLevel


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
        """获取别名数据"""
        url = f"{cls._base_url()}/warframe/alias.json"
        return await fetch_json_with_retry(
            url,
            log_templates={
                RetryLogLevel.WARNING: "获取别名数据失败（第 {attempt}/{max_retries} 次），{retry_delay} 秒后重试...",
                RetryLogLevel.ERROR: "获取别名数据失败，已重试 {max_retries} 次，放弃",
            },
        )

    @classmethod
    async def fetch_nodes(cls) -> Optional[list[dict]]:
        """获取星图节点数据"""
        url = f"{cls._base_url()}/warframe/nodes.json"
        return await fetch_json_with_retry(
            url,
            log_templates={
                RetryLogLevel.WARNING: "获取星图节点数据失败（第 {attempt}/{max_retries} 次），{retry_delay} 秒后重试...",
                RetryLogLevel.ERROR: "获取星图节点数据失败，已重试 {max_retries} 次，放弃",
            },
        )

    @classmethod
    async def fetch_state_translations(cls) -> Optional[dict]:
        """获取翻译数据"""
        url = f"{cls._base_url()}/warframe/state_translation.json"
        return await fetch_json_with_retry(
            url,
            log_templates={
                RetryLogLevel.WARNING: "获取翻译数据失败（第 {attempt}/{max_retries} 次），{retry_delay} 秒后重试...",
                RetryLogLevel.ERROR: "获取翻译数据失败，已重试 {max_retries} 次，放弃",
            },
        )

    @classmethod
    async def fetch_rive_tion(cls) -> Optional[list[dict]]:
        """获取Riven Tion 紫卡属性查询参数"""
        url = f"{cls._base_url()}/warframe/market_riven_tion.json"
        return await fetch_json_with_retry(
            url,
            log_templates={
                RetryLogLevel.WARNING: "获取紫卡属性查询参数失败（第 {attempt}/{max_retries} 次），{retry_delay} 秒后重试...",
                RetryLogLevel.ERROR: "获取紫卡属性查询参数失败，已重试 {max_retries} 次，放弃",
            },
        )

    @classmethod
    async def fetch_riven_tion_alias(cls) -> Optional[list[dict]]:
        """获取Riven Tion Alias 紫卡属性查询别名"""
        url = f"{cls._base_url()}/warframe/market_riven_tion_alias.json"
        return await fetch_json_with_retry(
            url,
            log_templates={
                RetryLogLevel.WARNING: "获取紫卡属性查询别名失败（第 {attempt}/{max_retries} 次），{retry_delay} 秒后重试...",
                RetryLogLevel.ERROR: "获取紫卡属性查询别名失败，已重试 {max_retries} 次，放弃",
            },
        )

    @classmethod
    async def fetch_reward_pool(cls) -> Optional[list[dict]]:
        """获取 奖励池 数据"""
        url = f"{cls._base_url()}/warframe/reward_pool.json"
        return await fetch_json_with_retry(
            url,
            log_templates={
                RetryLogLevel.WARNING: "获取奖励池数据失败（第 {attempt}/{max_retries} 次），{retry_delay} 秒后重试...",
                RetryLogLevel.ERROR: "获取奖励池数据失败，已重试 {max_retries} 次，放弃",
            },
        )

    @classmethod
    async def fetch_riven_analyse_trend(cls) -> Optional[list[dict]]:
        """获取 紫卡计算器 数据"""
        url = f"{cls._base_url()}/warframe/riven_analyse_trend.json"
        return await fetch_json_with_retry(
            url,
            log_templates={
                RetryLogLevel.WARNING: "获取紫卡计算器数据失败（第 {attempt}/{max_retries} 次），{retry_delay} 秒后重试...",
                RetryLogLevel.ERROR: "获取紫卡计算器数据失败，已重试 {max_retries} 次，放弃",
            },
        )