"""运行期日志降噪 / Runtime log noise filter

AstrBot 的 ``StarManager._unbind_plugin()`` 在每次重载插件时，会为每个已注册的
handler 打一条::

    Removed handler wf_alerts from plugin astrbot_plugin_nyxbot (48)

本插件有 31 条指令 + 1 个结果装饰器，一次重载就是 30+ 行 INFO，把真正有用的
日志全冲掉了。

这些信息对开发没有价值，但又不该去改框架源码，所以改为**运行期**给
``logging.getLogger("astrbot")`` 挂一个 Filter，按消息前缀丢弃。

为什么挂在 ``astrbot`` 这个 logger 上有效：``star_manager`` 是
``from astrbot.core import logger`` 直接调用，记录由该 logger 直接产生；
logger 自身的 filter 对「直接输出」的记录生效（注意：对子 logger 传播上来的
记录不生效，所以这里只拦核心 logger 自己的噪音）。
"""
from __future__ import annotations

import logging

# 需要抑制的消息前缀（都是重载时按 handler/module 逐条打印的批量日志）
_SUPPRESSED_PREFIXES: tuple[str, ...] = (
    "Removed handler ",
    "Removed module ",
)

# 标记属性，用于幂等安装（插件重载会重复执行本模块）
_MARKER = "_nyxbot_noise_filter"


class _ReloadNoiseFilter(logging.Filter):
    """丢弃插件重载时逐条打印的 handler/module 移除日志。"""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001 - 格式化失败时放行，避免吞掉日志
            return True
        return not message.startswith(_SUPPRESSED_PREFIXES)


def install_reload_noise_filter() -> None:
    """幂等地给核心 logger 装上降噪过滤器。"""
    core_logger = logging.getLogger("astrbot")
    if any(getattr(f, _MARKER, False) for f in core_logger.filters):
        return

    noise_filter = _ReloadNoiseFilter()
    setattr(noise_filter, _MARKER, True)
    core_logger.addFilter(noise_filter)
