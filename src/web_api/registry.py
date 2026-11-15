"""Plugin Pages 后端 API 注册入口

集中注册所有 Plugin Pages 的 Web API 端点。
"""
from __future__ import annotations

from typing import Any

from astrbot.api.star import Context

from .data_admin import register_data_apis
from .relic_studio import register_relic_studio_apis
from .settings import register_settings_apis


def register_web_apis(context: Context, config: Any = None) -> None:
    """注册所有 Plugin Pages Web API。

    Args:
        context: AstrBot 上下文实例。
        config: 插件持有的 ``AstrBotConfig``，设置接口用它做内存写入；
            缺省时退化为直接读写配置文件。
    """
    register_data_apis(context)
    register_relic_studio_apis(context)
    register_settings_apis(context, config)
