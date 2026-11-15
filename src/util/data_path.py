from __future__ import annotations

# ==================================================================
# 获取数据存放目录
# ==================================================================
from pathlib import Path

from astrbot.api.star import StarTools

from .metadata import get_plugin_name

#: 进程内缓存的数据目录。目录在启动后不变，无需每次重算。
_CACHED_DATA_DIR: Path | None = None


def get_public_data_path() -> str:
    """获取插件文件路径（框架规范目录 ``data/plugin_data/<插件名>``）。

    审查 P1-5：改用框架约定的 ``StarTools.get_data_dir()``，不再手工拼
    ``get_astrbot_plugin_data_path()``，路径语义与 AstrBot 保持同步。

    注意必须**显式传插件名**：框架在缺省时会用 ``star_map`` 反查调用方
    模块，而 ``data_path`` 不是注册过的插件主模块，反查必然抛
    ``RuntimeError``。显式传名后不依赖框架初始化状态，模块导入期也可用
    （``export_downloader`` 在导入时就取路径）。
    """
    global _CACHED_DATA_DIR

    if _CACHED_DATA_DIR is None:
        _CACHED_DATA_DIR = Path(StarTools.get_data_dir(get_plugin_name()))
    return str(_CACHED_DATA_DIR)
