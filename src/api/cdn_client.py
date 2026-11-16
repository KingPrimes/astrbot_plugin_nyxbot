"""CDN client / CDN 客户端

封装从 CDN 获取 Warframe 配置数据（别名、节点等）的接口。
"""
from __future__ import annotations

import asyncio

from cachetools import TTLCache

from astrbot.api import logger

from ..config import get_wf_data_source_cdn
from ..util import (
    RetryLogLevel,
    fetch_json_with_retry,
)

GITHUB_TAGS_URL = "https://api.github.com/repos/KingPrimes/DataSource/tags"
_tag_cache: TTLCache = TTLCache(maxsize=1, ttl=120)
_tag_lock: asyncio.Lock | None = None


class CdnClient:
    """CDN 客户端。

    用于从 CDN 获取 Warframe 辅助数据，如别名映射、星图节点等。
    """

    @classmethod
    async def _get_latest_tag(cls) -> str:
        """获取 DataSource 仓库的最新 tag，带 2 分钟缓存 + 防惊群锁。"""
        global _tag_lock
        cache_key = "latest_tag"
        if cache_key in _tag_cache:
            return _tag_cache[cache_key]
        if _tag_lock is None:
            _tag_lock = asyncio.Lock()
        async with _tag_lock:
            # 双重检查：等待锁期间其他协程可能已填充缓存
            if cache_key in _tag_cache:
                return _tag_cache[cache_key]
            data = await fetch_json_with_retry(
                GITHUB_TAGS_URL,
                log_templates={
                    RetryLogLevel.WARNING:  (
                        "获取最新版本号失败（第 {attempt}/{max_retries} 次），"
                        "{retry_delay} 秒后重试..."
                    ),
                    RetryLogLevel.ERROR: "获取最新版本号失败，已重试 {max_retries} 次，将回退使用 @latest",
                },
            )
            tag: str = data[0]["name"] if data else ""
            _tag_cache[cache_key] = tag
            if tag:
                logger.info(f"获取到 DataSource 最新版本: {tag}")
            else:
                logger.warning("未能获取 DataSource 版本号，将回退使用 @latest")
            return tag

    @classmethod
    async def get_latest_tag(cls) -> str:
        """获取 DataSource 仓库最新 tag（公开入口，带 2 分钟缓存）。"""
        return await cls._get_latest_tag()

    @classmethod
    async def _base_url(cls) -> str:
        """获取当前配置的 CDN 基础 URL，自动拼接最新版本号。

        配置默认值以 ``@`` 结尾（``.../DataSource@``），正常路径拼成
        ``...@v1.0.3`` 精确 pin 到 tag。拿不到 tag 时**不能**保留结尾的
        ``@``——jsDelivr 会把空版本号当坏请求返回 400（曾导致整套 CDN 数据
        静默全部丢失）；也不宜直接去掉 ``@``，那会落到默认分支 HEAD（可能是
        未发布的半成品）。改用 ``@latest``，由 jsDelivr 解析到最新 tag，
        语义与正常路径一致。
        """
        base = get_wf_data_source_cdn()
        if base.endswith("@"):
            tag = await cls._get_latest_tag()
            if tag:
                return base + tag
            # 回退 @latest（失败提示由 _get_latest_tag 打一次，这里不重复刷屏）
            return base + "latest"
        return base

    @classmethod
    async def fetch_alias(cls) -> list[dict] | None:
        """获取别名数据"""
        url = f"{await cls._base_url()}/warframe/alias.json"
        return await fetch_json_with_retry(
            url,
            log_templates={
                RetryLogLevel.WARNING: "获取别名数据失败（第 {attempt}/{max_retries} 次），{retry_delay} 秒后重试...",
                RetryLogLevel.ERROR: "获取别名数据失败，已重试 {max_retries} 次，放弃",
            },
        )

    @classmethod
    async def fetch_nodes(cls) -> list[dict] | None:
        """获取星图节点数据"""
        url = f"{await cls._base_url()}/warframe/nodes.json"
        return await fetch_json_with_retry(
            url,
            log_templates={
                RetryLogLevel.WARNING:  (
                    "获取星图节点数据失败（第 {attempt}/{max_retries} 次），"
                    "{retry_delay} 秒后重试..."
                ),
                RetryLogLevel.ERROR: "获取星图节点数据失败，已重试 {max_retries} 次，放弃",
            },
        )

    @classmethod
    async def fetch_arbitration_tiers(cls) -> list[dict] | None:
        """获取仲裁节点分级数据（warframe/arbitration_tiers.json）。"""
        url = f"{await cls._base_url()}/warframe/arbitration_tiers.json"
        return await fetch_json_with_retry(
            url,
            log_templates={
                RetryLogLevel.WARNING:  (
                    "获取仲裁分级数据失败（第 {attempt}/{max_retries} 次），"
                    "{retry_delay} 秒后重试..."
                ),
                RetryLogLevel.ERROR: "获取仲裁分级数据失败，已重试 {max_retries} 次，放弃",
            },
        )

    @classmethod
    async def fetch_state_translations(cls) -> list[dict] | None:
        """获取翻译数据"""
        url = f"{await cls._base_url()}/warframe/state_translation.json"
        return await fetch_json_with_retry(
            url,
            log_templates={
                RetryLogLevel.WARNING: "获取翻译数据失败（第 {attempt}/{max_retries} 次），{retry_delay} 秒后重试...",
                RetryLogLevel.ERROR: "获取翻译数据失败，已重试 {max_retries} 次，放弃",
            },
        )

    @classmethod
    async def fetch_riven_tion(cls) -> list[dict] | None:
        """获取Riven Tion 紫卡属性查询参数"""
        url = f"{await cls._base_url()}/warframe/market_riven_tion.json"
        return await fetch_json_with_retry(
            url,
            log_templates={
                RetryLogLevel.WARNING:  (
                    "获取紫卡属性查询参数失败（第 {attempt}/{max_retries} 次），"
                    "{retry_delay} 秒后重试..."
                ),
                RetryLogLevel.ERROR: "获取紫卡属性查询参数失败，已重试 {max_retries} 次，放弃",
            },
        )

    @classmethod
    async def fetch_riven_tion_alias(cls) -> list[dict] | None:
        """获取Riven Tion Alias 紫卡属性查询别名"""
        url = f"{await cls._base_url()}/warframe/market_riven_tion_alias.json"
        return await fetch_json_with_retry(
            url,
            log_templates={
                RetryLogLevel.WARNING:  (
                    "获取紫卡属性查询别名失败（第 {attempt}/{max_retries} 次），"
                    "{retry_delay} 秒后重试..."
                ),
                RetryLogLevel.ERROR: "获取紫卡属性查询别名失败，已重试 {max_retries} 次，放弃",
            },
        )

    @classmethod
    async def fetch_reward_pool(cls) -> list[dict] | None:
        """获取 奖励池 数据"""
        url = f"{await cls._base_url()}/warframe/reward_pool.json"
        return await fetch_json_with_retry(
            url,
            log_templates={
                RetryLogLevel.WARNING: "获取奖励池数据失败（第 {attempt}/{max_retries} 次），{retry_delay} 秒后重试...",
                RetryLogLevel.ERROR: "获取奖励池数据失败，已重试 {max_retries} 次，放弃",
            },
        )

    @classmethod
    async def fetch_riven_analyse_trend(cls) -> list[dict] | None:
        """获取 紫卡计算器 数据"""
        url = f"{await cls._base_url()}/warframe/riven_analyse_trend.json"
        return await fetch_json_with_retry(
            url,
            log_templates={
                RetryLogLevel.WARNING:  (
                    "获取紫卡计算器数据失败（第 {attempt}/{max_retries} 次），"
                    "{retry_delay} 秒后重试..."
                ),
                RetryLogLevel.ERROR: "获取紫卡计算器数据失败，已重试 {max_retries} 次，放弃",
            },
        )
