from __future__ import annotations

# ==================================================================
# 获取数据存放目录
# ==================================================================
from pathlib import Path

from astrbot.core.utils.astrbot_path import get_astrbot_plugin_data_path

from .metadata import get_plugin_name

#: 进程内缓存的数据目录。目录在启动后不变，无需每次重算。
_CACHED_DATA_DIR: Path | None = None


def get_public_data_path() -> str:
    """获取插件文件路径，使用 AstrBot 指定的数据目录"""
    global _CACHED_DATA_DIR

    if _CACHED_DATA_DIR is None:
        data_dir = Path(get_astrbot_plugin_data_path()) / get_plugin_name()
        if not data_dir.exists():  # 已存在时跳过 mkdir，热路径不做多余系统调用
            data_dir.mkdir(parents=True, exist_ok=True)
        _CACHED_DATA_DIR = data_dir
    return str(_CACHED_DATA_DIR)
