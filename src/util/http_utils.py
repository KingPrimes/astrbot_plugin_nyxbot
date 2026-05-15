"""HTTP utilities / HTTP 客户端封装

基于 aiohttp 的异步 HTTP 客户端封装，提供统一的请求接口和错误处理。
"""
from __future__ import annotations

import asyncio
from enum import Enum
from typing import Any, Optional

import aiohttp
from astrbot.api import logger


class RetryLogLevel(Enum):
    """重试日志等级枚举，用于 fetch_json_with_retry 的 log_templates 参数。"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

# 默认超时设置（秒）
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=30)

# 共享的 ClientSession 单例
_session: Optional[aiohttp.ClientSession] = None


async def get_session() -> aiohttp.ClientSession:
    """获取全局共享的 ClientSession 实例。

    复用 ClientSession 以利用连接池，提升性能。
    """
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(
            timeout=DEFAULT_TIMEOUT,
            headers={
                "User-Agent": "NyxBot-AstrBot/1.0",
                "Accept": "application/json",
            },
        )
    return _session


async def close_session() -> None:
    """关闭全局 ClientSession。"""
    global _session
    if _session and not _session.closed:
        await _session.close()
    _session = None


async def fetch_json(
    url: str,
    params: Optional[dict[str, Any]] = None,
    headers: Optional[dict[str, str]] = None,
    timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT,
    content_type: Optional[str] = None,
) -> Optional[Any]:
    """发送 GET 请求并返回 JSON 响应。

    Args:
        url: 请求 URL。
        params: 查询参数。
        headers: 额外请求头。
        timeout: 超时设置。
        content_type: 强制指定 content_type（某些 API 返回类型不标准）。

    Returns:
        解析后的 JSON 数据，失败返回 None。
    """
    session = await get_session()
    try:
        async with session.get(
            url,
            params=params,
            headers=headers,
            timeout=timeout,
        ) as resp:
            if resp.status < 200 or resp.status >= 300:
                logger.warning(f"HTTP {resp.status} 请求失败: {url}")
                return None
            return await resp.json(content_type=content_type)
    except asyncio.TimeoutError:
        logger.error(f"请求超时: {url}")
        return None
    except aiohttp.ClientError as e:
        logger.error(f"HTTP 请求错误: {url} - {e}")
        return None
    except Exception as e:
        logger.error(f"未知错误: {url} - {e}")
        return None


async def fetch_text(
    url: str,
    params: Optional[dict[str, Any]] = None,
    headers: Optional[dict[str, str]] = None,
    timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT,
) -> Optional[str]:
    """发送 GET 请求并返回文本响应。

    Args:
        url: 请求 URL。
        params: 查询参数。
        headers: 额外请求头。
        timeout: 超时设置。

    Returns:
        响应文本，失败返回 None。
    """
    session = await get_session()
    try:
        async with session.get(url, params=params, headers=headers, timeout=timeout) as resp:
            if resp.status < 200 or resp.status >= 300:
                logger.warning(f"HTTP {resp.status} 请求失败: {url}")
                return None
            return await resp.text()
    except asyncio.TimeoutError:
        logger.error(f"请求超时: {url}")
        return None
    except aiohttp.ClientError as e:
        logger.error(f"HTTP 请求错误: {url} - {e}")
        return None
    except Exception as e:
        logger.error(f"请求失败: {url} - {e}")
        return None


# 默认重试日志模板
_DEFAULT_LOG_TEMPLATES: dict[RetryLogLevel, str] = {
    RetryLogLevel.WARNING: (
        "请求失败（第 {attempt}/{max_retries} 次），"
        "{retry_delay} 秒后重试... URL: {url}"
    ),
    RetryLogLevel.ERROR: (
        "请求失败，已重试 {max_retries} 次，放弃。URL: {url}"
    ),
}


async def fetch_json_with_retry(
    url: str,
    params: Optional[dict[str, Any]] = None,
    headers: Optional[dict[str, str]] = None,
    timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT,
    content_type: Optional[str] = None,
    max_retries: int = 3,
    retry_delay: float = 5.0,
    log_templates: Optional[dict[RetryLogLevel, str]] = None,
) -> Optional[Any]:
    """带自动重试的 GET JSON 请求。

    Args:
        url: 请求 URL。
        params: 查询参数。
        headers: 额外请求头。
        timeout: 超时设置。
        content_type: 强制指定 content_type。
        max_retries: 最大重试次数（默认 3）。
        retry_delay: 重试间隔秒数（默认 5）。
        log_templates: 自定义日志模板，key 为 RetryLogLevel 枚举成员，
            value 为模板字符串。支持的占位符：
            {url}, {attempt}, {max_retries}, {retry_delay}
            未提供的等级使用默认模板；传空字符串可禁用该等级日志。

    Returns:
        解析后的 JSON 数据，重试超限后返回 None。
    """
    templates = {**_DEFAULT_LOG_TEMPLATES, **(log_templates or {})}

    for attempt in range(1, max_retries + 1):
        data = await fetch_json(
            url, params=params, headers=headers,
            timeout=timeout, content_type=content_type,
        )
        if data is not None:
            info_tpl = templates.get(RetryLogLevel.INFO)
            if info_tpl:
                logger.info(info_tpl.format(
                    url=url, attempt=attempt,
                    max_retries=max_retries, retry_delay=retry_delay,
                ))
            return data

        if attempt < max_retries:
            warn_tpl = templates.get(RetryLogLevel.WARNING)
            if warn_tpl:
                logger.warning(warn_tpl.format(
                    url=url, attempt=attempt,
                    max_retries=max_retries, retry_delay=retry_delay,
                ))
            await asyncio.sleep(retry_delay)

    err_tpl = templates.get(RetryLogLevel.ERROR)
    if err_tpl:
        logger.error(err_tpl.format(
            url=url, attempt=max_retries,
            max_retries=max_retries, retry_delay=retry_delay,
        ))
    return None
