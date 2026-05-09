"""Plugin configuration loader / 插件配置加载器

根据 _conf_schema.json 中定义的配置项结构，
从 AstrBot 插件配置文件中加载配置值，并提供类型安全的访问接口。
当配置文件中缺少某项时，自动回退到 schema 中定义的默认值。
"""

from __future__ import annotations

import json
import os
from typing import Any
from astrbot.core.utils.astrbot_path import get_astrbot_config_path
from ..util import get_plugin_name


class PluginConfig:
    """插件配置解析类，负责加载 schema 和配置文件并提供类型安全的访问。

    根据 _conf_schema.json 中定义的配置项结构，
    从 AstrBot 插件配置文件（data/config/<plugin_name>_config.json）中加载配置值。
    当配置文件中缺少某项时，自动回退到 schema 中定义的默认值。
    """

    def __init__(self, schema_path: str, config_path: str) -> None:
        self._schema_path = schema_path
        self._config_path = config_path
        self._schema: dict[str, Any] = {}
        self._config: dict[str, Any] = {}

        self._load_schema()
        self._load_config()

    # --- Class factory / 类工厂方法 ---

    @classmethod
    def from_plugin_dir(cls, plugin_dir: str | None = None) -> PluginConfig:
        """根据插件目录创建 PluginConfig 实例。

        Args:
            plugin_dir: 插件目录路径，默认为当前文件所在目录。

        Returns:
            PluginConfig 实例。
        """
        if plugin_dir is None:
            plugin_dir = os.path.dirname(os.path.abspath(__file__))

        schema_path = os.path.join(plugin_dir, "_conf_schema.json")

        # 通过 AstrBot 提供的接口获取配置目录
        config_dir = get_astrbot_config_path()
        # 通过 metadata.yaml 获取插件名称
        plugin_name = get_plugin_name()
        config_path = os.path.join(config_dir, f"{plugin_name}_config.json")

        return cls(schema_path=schema_path, config_path=config_path)

    # --- Loading / 加载 ---

    def _load_schema(self) -> None:
        """加载 _conf_schema.json 配置模板。"""
        try:
            if os.path.exists(self._schema_path):
                with open(self._schema_path, encoding="utf-8") as f:
                    self._schema = json.load(f)
        except Exception:
            self._schema = {}

    def _load_config(self) -> None:
        """加载 AstrBot 插件配置文件。"""
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, encoding="utf-8") as f:
                    self._config = json.load(f)
        except Exception:
            self._config = {}

    def reload(self) -> None:
        """重新加载配置文件（schema + config）。

        适用于插件热重载场景，修改配置后调用此方法刷新内存中的值。
        """
        self._load_schema()
        self._load_config()

    # --- Generic access / 通用访问 ---

    def get(self, key: str, fallback: Any = None) -> Any:
        """获取配置值，优先从配置文件读取，缺失时回退到 schema 默认值。

        Args:
            key: 配置项名称。
            fallback: 当配置文件和 schema 中均未定义时的回退值。

        Returns:
            配置值。
        """
        # 1. 配置文件中的值优先
        if key in self._config:
            return self._config[key]

        # 2. 回退到 schema 中定义的默认值
        if key in self._schema:
            return self._schema[key].get("default", fallback)

        return fallback

    # --- Typed properties / 类型化属性 ---

    @property
    def wf_update_interval(self) -> int:
        """世界状态更新间隔（秒）。"""
        return int(self.get("wf_update_interval", 600))

    @property
    def wf_notification_retention_hours(self) -> int:
        """通知历史保留时长（小时）。"""
        return int(self.get("wf_notification_retention_hours", 12))

    @property
    def wf_data_source_cdn(self) -> str:
        """数据源CDN地址。"""
        return str(self.get("wf_data_source_cdn", "https://testingcf.jsdelivr.net/gh/KingPrimes/DataSource"))

    @property
    def wf_arbitration_data(self) -> str:
        """Warframe仲裁数据源Url地址。"""
        return str(self.get("wf_arbitration_data", "https://wf.555590.xyz/api/arbys?days=30"))

    @property
    def wf_command_prefix(self) -> str:
        """Warframe 助手指令前缀，为空时指令无需前缀即可触发。"""
        return str(self.get("wf_command_prefix", "")).strip()

    # --- Representation / 表示 ---

    def __repr__(self) -> str:
        keys = list(self._schema.keys())
        return f"PluginConfig(keys={keys}, config_path={self._config_path!r})"


# --- 模块级单例与便捷函数 ---

_default_config: PluginConfig | None = None


def _get_default_config() -> PluginConfig:
    """获取默认的 PluginConfig 单例实例。"""
    global _default_config
    if _default_config is None:
        _default_config = PluginConfig.from_plugin_dir()
    return _default_config


def get_wf_update_interval() -> int:
    """获取世界状态更新间隔（秒）。"""
    return _get_default_config().wf_update_interval


def get_wf_notification_retention_hours() -> int:
    """获取通知历史保留时长（小时）。"""
    return _get_default_config().wf_notification_retention_hours


def get_wf_data_source_cdn() -> str:
    """获取数据源CDN地址。"""
    return _get_default_config().wf_data_source_cdn


def get_wf_arbitration_data() -> str:
    """获取Warframe仲裁数据源Url地址。"""
    return _get_default_config().wf_arbitration_data


def get_wf_command_prefix() -> str:
    """获取Warframe 助手指令前缀，为空时指令无需前缀即可触发。"""
    return _get_default_config().wf_command_prefix
