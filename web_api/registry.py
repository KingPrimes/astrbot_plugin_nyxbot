"""Plugin Pages 后端 API 注册入口

集中注册所有 Plugin Pages 的 Web API 端点。
"""
from __future__ import annotations

from astrbot.api.star import Context

from ..web_api.data_admin import register_data_apis


def register_web_apis(context: Context) -> None:
    """注册所有 Plugin Pages Web API。

    Args:
        context: AstrBot 上下文实例。
    """
    register_data_apis(context)
