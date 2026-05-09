"""HTTP utilities / HTTP 客户端封装

基于 aiohttp 的异步 HTTP 客户端封装，提供统一的请求接口和错误处理。
"""
from __future__ import annotations

import asyncio
from typing import Any, Optional

import aiohttp
from astrbot.api import logger

# 默认超时设置（秒）
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=30)
LONG_TIMEOUT = aiohttp.ClientTimeout(total=120)

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
    timeout: Optional[aiohttp.ClientTimeout] = None,
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
            timeout=timeout or DEFAULT_TIMEOUT,
        ) as resp:
            if resp.status != 200:
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
) -> Optional[str]:
    """发送 GET 请求并返回文本响应。

    Args:
        url: 请求 URL。
        params: 查询参数。
        headers: 额外请求头。

    Returns:
        响应文本，失败返回 None。
    """
    session = await get_session()
    try:
        async with session.get(url, params=params, headers=headers) as resp:
            if resp.status != 200:
                logger.warning(f"HTTP {resp.status} 请求失败: {url}")
                return None
            return await resp.text()
    except Exception as e:
        logger.error(f"请求失败: {url} - {e}")
        return None
