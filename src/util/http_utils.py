"""HTTP utilities / HTTP 客户端封装

基于 aiohttp 的异步 HTTP 客户端封装，提供统一的请求接口和错误处理。
"""
from __future__ import annotations

import asyncio
import os
import random
from enum import Enum
from pathlib import Path
from typing import Any

import aiohttp

from astrbot.api import logger


class RetryLogLevel(Enum):
    """重试日志等级枚举，用于 fetch_json_with_retry 的 log_templates 参数。"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class HttpMethod(str, Enum):
    """HTTP 请求方法枚举。

    继承 str 以便直接传入 aiohttp 的 method 参数。
    """

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"

# 默认超时设置（秒）
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=30)

# 共享的 ClientSession 单例 + 线程安全锁
_session: aiohttp.ClientSession | None = None
_session_lock: asyncio.Lock | None = None


def _log_proxy_state() -> None:
    """创建会话时打印一次代理状态，便于排查「请求为什么走/没走代理」。"""
    proxy = os.environ.get("https_proxy") or os.environ.get("http_proxy") or ""
    if proxy:
        no_proxy = os.environ.get("no_proxy", "")
        logger.info(f"HTTP 会话使用 AstrBot 代理: {proxy}（no_proxy: {no_proxy or '未设置'}）")
    else:
        logger.info("HTTP 会话未使用代理（AstrBot 未配置 http_proxy），走直连")


async def get_session() -> aiohttp.ClientSession:
    """获取全局共享的 ClientSession 实例。

    复用 ClientSession 以利用连接池，提升性能。
    使用 asyncio.Lock 防止并发创建导致的连接泄漏。
    """
    global _session, _session_lock
    if _session is None or _session.closed:
        if _session_lock is None:
            _session_lock = asyncio.Lock()
        async with _session_lock:
            if _session is None or _session.closed:
                _session = aiohttp.ClientSession(
                    timeout=DEFAULT_TIMEOUT,
                    headers={
                        "User-Agent": "NyxBot-AstrBot/1.0",
                        "Accept": "application/json",
                    },
                    connector=aiohttp.TCPConnector(limit=20, limit_per_host=5),
                    # 跟随 AstrBot 的代理配置：框架在 core_lifecycle 里把
                    # cmd_config.json 的 http_proxy/no_proxy 写进同名环境变量，
                    # trust_env 让 aiohttp 每次请求时按它们解析代理
                    # （no_proxy 命中的地址自动直连，含 localhost）。
                    trust_env=True,
                )
                _log_proxy_state()
    return _session


async def close_session() -> None:
    """关闭全局 ClientSession。"""
    global _session
    if _session and not _session.closed:
        await _session.close()
    _session = None


async def _fetch(
    url: str,
    response_handler: Any,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT,
) -> Any | None:
    """内部通用 GET 请求 — 统一会话获取、状态码检查、异常处理。

    Args:
        url: 请求 URL。
        response_handler: 异步回调，接收 aiohttp.ClientResponse 并返回解析结果。
        params: 查询参数。
        headers: 额外请求头。
        timeout: 超时设置。

    Returns:
        response_handler 的返回值，失败返回 None。
    """
    session = await get_session()
    try:
        async with session.get(
            url, params=params, headers=headers, timeout=timeout,
        ) as resp:
            if resp.status < 200 or resp.status >= 300:
                logger.warning(f"HTTP {resp.status} 请求失败: {url}")
                return None
            return await response_handler(resp)
    except asyncio.TimeoutError:
        logger.error(f"请求超时: {url}")
        return None
    except aiohttp.ClientError as e:
        logger.error(f"HTTP 请求错误: {url} - {e}")
        return None
    except Exception as e:
        logger.error(f"未知错误: {url} - {e}")
        return None


async def fetch_json(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT,
    content_type: str | None = None,
) -> Any | None:
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
    return await _fetch(
        url, lambda resp: resp.json(content_type=content_type),
        params, headers, timeout,
    )


async def fetch_text(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT,
) -> str | None:
    """发送 GET 请求并返回文本响应。

    Args:
        url: 请求 URL。
        params: 查询参数。
        headers: 额外请求头。
        timeout: 超时设置。

    Returns:
        响应文本，失败返回 None。
    """
    return await _fetch(url, lambda resp: resp.text(), params, headers, timeout)


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
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT,
    content_type: str | None = None,
    max_retries: int = 3,
    retry_delay: float = 5.0,
    log_templates: dict[RetryLogLevel, str] | None = None,
) -> Any | None:
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
            delay = retry_delay * (2 ** (attempt - 1))
            delay += random.uniform(0, delay * 0.5)  # jitter
            await asyncio.sleep(delay)

    err_tpl = templates.get(RetryLogLevel.ERROR)
    if err_tpl:
        logger.error(err_tpl.format(
            url=url, attempt=max_retries,
            max_retries=max_retries, retry_delay=retry_delay,
        ))
    return None


async def download_file(
    url: str,
    method: HttpMethod = HttpMethod.GET,
    request_body: Any | None = None,
    extra_headers: dict[str, str] | None = None,
    output: str | Path = "download.tmp",
    timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT,
    chunk_size: int = 65536,
    show_progress: bool = True,
) -> bool:
    """通过 HTTP 请求下载文件并保存到本地。

    支持任意 HTTP 方法、自定义请求头、JSON 请求体，采用流式分块写入
    以避免大文件撑爆内存。

    Args:
        url: 请求 URL。
        method: HTTP 方法，默认 GET。
        request_body: JSON 请求体，传入 None 时不发送 body。
        extra_headers: 额外请求头，会合并到默认头之后。
        output: 输出文件路径，默认 "download.tmp"。
        timeout: 超时设置。
        chunk_size: 流式读取块大小（字节），默认 65536 (64KB)。
        show_progress: 是否输出下载进度日志，默认 True。

    Returns:
        bool: 下载成功返回 True，失败返回 False。
    """
    # 构建默认请求头
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept-Encoding": "application/octet-stream",
    }
    if extra_headers:
        headers.update(extra_headers)

    session = await get_session()
    output_path = Path(output)
    # 确保目标目录存在 — 异步化避免阻塞事件循环
    await asyncio.to_thread(output_path.parent.mkdir, parents=True, exist_ok=True)

    # 构造请求参数
    kwargs: dict[str, Any] = {
        "url": url,
        "headers": headers,
        "timeout": timeout,
    }
    if request_body is not None:
        kwargs["json"] = request_body

    try:
        async with session.request(method.value, **kwargs) as resp:
            if resp.status < 200 or resp.status >= 300:
                logger.warning(
                    f"downloadFile 失败: {url} "
                    f"状态码={resp.status} 响应头={dict(resp.headers)}"
                )
                return False

            # 流式读取并异步写入文件，避免同步 I/O 阻塞事件循环
            total_read = 0
            loop = asyncio.get_running_loop()
            with open(output_path, "wb") as f:
                while True:
                    chunk = await resp.content.read(chunk_size)
                    if not chunk:
                        break
                    await loop.run_in_executor(None, f.write, chunk)
                    total_read += len(chunk)
                    if show_progress and total_read % (1024 * 1024) < chunk_size:
                        logger.info(
                            f"下载进度: {url} — {total_read} bytes"
                        )
            return True

    except asyncio.TimeoutError:
        logger.error(f"downloadFile 超时: {url}")
        return False
    except aiohttp.ClientError as e:
        logger.error(f"downloadFile 网络错误: {url} - {e}")
        return False
    except Exception as e:
        logger.error(f"downloadFile 未知错误: {url} - {e}")
        return False
