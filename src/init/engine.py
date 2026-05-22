"""
Tortoise ORM Engine Lifecycle / Tortoise ORM 引擎生命周期

提供数据库引擎的单例初始化、关闭，以及初始化完成信号量。
从 data_sources_init.py 中抽离，消除 service 层对 init 层的循环依赖。
"""
from __future__ import annotations

import asyncio
import logging
import os

from tortoise import Tortoise

from astrbot.api import logger

from ..config import get_db_debug
from ..util import get_public_data_path

# ============================================================
# 初始化完成信号量（供命令/API 等待初始化完成）
# ============================================================
_init_complete: asyncio.Event = asyncio.Event()


def set_init_complete() -> None:
    """标记初始化完成，唤醒所有等待者。"""
    _init_complete.set()


async def init_ready() -> None:
    """阻塞等待直到数据初始化完成。命令执行前可调用此函数确保数据就绪。"""
    await _init_complete.wait()


# ============================================================
# Tortoise ORM 模型模块路径
#
# AstrBot 以完全限定包名加载插件（如 data.plugins.astrbot_plugin_nyxbot），
# 因此从 __name__ 可以动态推导出完整的模型模块路径。
#
# 示例：
#   __name__ = "data.plugins.astrbot_plugin_nyxbot.src.init.engine"
#   ↓ rsplit(".", 2)[0] + ".model"
#   = "data.plugins.astrbot_plugin_nyxbot.src.model"
#
# 这样 Tortoise ORM 使用 importlib.import_module() 导入的模块，
# 与插件自身相对导入的模块在 sys.modules 中拥有相同的 key，
# 从而彻底避免"双模块冲突"问题。
# ============================================================
_MODEL_MODULE = __name__.rsplit(".", 2)[0] + ".model"
_MODELS_MODULES = [_MODEL_MODULE]

_tortoise_initialized: bool = False


async def get_engine():
    """初始化 Tortoise ORM 并建表（单例）。"""
    _db_path: str = os.path.join(get_public_data_path(), "nyxbot.db")
    logger.debug(f"数据库路径: {_db_path}")
    global _tortoise_initialized
    if not _tortoise_initialized:
        # 根据配置开关控制 Tortoise ORM 的 SQL 日志输出
        if get_db_debug():
            logging.getLogger("tortoise.db_client").setLevel(logging.DEBUG)
            logging.getLogger("tortoise").setLevel(logging.DEBUG)
            logger.info("数据库调试模式已启用")
        else:
            logging.getLogger("tortoise.db_client").setLevel(logging.INFO)
            logging.getLogger("tortoise").setLevel(logging.INFO)

        db_url = f"sqlite://{_db_path}"
        await Tortoise.init(
            db_url=db_url,
            modules={"models": _MODELS_MODULES},
        )
        await Tortoise.generate_schemas()
        _tortoise_initialized = True
    return Tortoise.get_connection("default")


async def close_engine() -> None:
    """关闭 TortoiseORM 连接。"""
    global _tortoise_initialized
    if _tortoise_initialized:
        await Tortoise.close_connections()
        _tortoise_initialized = False
        logger.info("TortoiseORM connections closed")
