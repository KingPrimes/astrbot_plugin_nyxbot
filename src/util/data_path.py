# ==================================================================
# 获取数据存放目录
# ==================================================================
from pathlib import Path
from astrbot.core.utils.astrbot_path import get_astrbot_plugin_data_path
from .metadata import get_plugin_name

def _get_db_path() -> str:
    """获取数据库文件路径，使用 AstrBot 指定的数据目录"""
    data_dir = Path(get_astrbot_plugin_data_path()) / get_plugin_name()
    data_dir.mkdir(parents=True,exist_ok=True)
    return str(data_dir)