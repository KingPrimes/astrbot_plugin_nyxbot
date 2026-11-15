"""Plugin configuration loader / 插件配置加载器

根据 _conf_schema.json 中定义的配置项结构，
从 AstrBot 插件配置文件中加载配置值，并提供类型安全的访问接口。
当配置文件中缺少某项时，自动回退到 schema 中定义的默认值。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import orjson

from astrbot.api import logger
from astrbot.core.utils.astrbot_path import get_astrbot_config_path

from ..util import get_plugin_name

# --- 数据初始化模式 ---
DATA_INIT_MODE_AUTO = "auto"
DATA_INIT_MODE_ALWAYS = "always"
DATA_INIT_MODE_NEVER = "never"
DATA_INIT_MODE_OFFLINE = "offline"
_DATA_INIT_MODES = (
    DATA_INIT_MODE_AUTO,
    DATA_INIT_MODE_ALWAYS,
    DATA_INIT_MODE_NEVER,
    DATA_INIT_MODE_OFFLINE,
)

# 旧配置项（v1 早期版本使用，仅用于启动时兼容映射）
_LEGACY_ENV_KEY = "wf_runtime_env"
_LEGACY_FORCE_KEY = "wf_data_force_sync"


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
            plugin_dir = str(Path(__file__).resolve().parent.parent.parent)

        schema_path = str(Path(plugin_dir) / "_conf_schema.json")

        # 通过 AstrBot 提供的接口获取配置目录
        config_dir = get_astrbot_config_path()
        # 通过 metadata.yaml 获取插件名称
        plugin_name = get_plugin_name()
        config_path = str(Path(config_dir) / f"{plugin_name}_config.json")

        return cls(schema_path=schema_path, config_path=config_path)

    # --- Loading / 加载 ---

    def _load_schema(self) -> None:
        """加载 _conf_schema.json 配置模板。"""
        try:
            if Path(self._schema_path).exists():
                self._schema = orjson.loads(
                    Path(self._schema_path).read_text(encoding="utf-8-sig")
                )
        except Exception:
            logger.warning("加载 _conf_schema.json 失败，使用空 schema")
            self._schema = {}

    def _load_config(self) -> None:
        """加载 AstrBot 插件配置文件。"""
        try:
            if Path(self._config_path).exists():
                self._config = orjson.loads(
                    Path(self._config_path).read_text(encoding="utf-8-sig")
                )
        except Exception:
            logger.warning("加载插件配置文件失败，使用空配置")
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
    def wf_data_init_mode(self) -> str:
        """数据初始化模式（auto / always / never / offline）。"""
        # 只认配置文件里显式写入的值，缺失时才走旧配置映射
        raw = self._config.get("wf_data_init_mode")
        if raw is None:
            return self._legacy_data_init_mode()

        normalized = str(raw).strip().lower()
        if normalized in _DATA_INIT_MODES:
            return normalized

        logger.warning(f"未知的 wf_data_init_mode={raw!r}，回退 auto")
        return self._legacy_data_init_mode()

    def _legacy_data_init_mode(self) -> str:
        """从旧配置（wf_runtime_env + wf_data_force_sync）推导初始化模式。"""
        if bool(self.get(_LEGACY_FORCE_KEY, False)):
            return DATA_INIT_MODE_ALWAYS
        legacy_env = str(self.get(_LEGACY_ENV_KEY, "")).strip().lower()
        if legacy_env == "development":
            return DATA_INIT_MODE_NEVER
        if legacy_env == "testing":
            return DATA_INIT_MODE_OFFLINE
        return DATA_INIT_MODE_AUTO

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
        return str(self.get("wf_data_source_cdn", "https://testingcf.jsdelivr.net/gh/KingPrimes/DataSource@"))

    @property
    def wf_command_prefix(self) -> str:
        """Warframe 助手指令前缀，为空时指令无需前缀即可触发。"""
        return str(self.get("wf_command_prefix", "")).strip()

    @property
    def db_debug(self) -> bool:
        """数据库调试模式开关，开启后输出 Tortoise ORM SQL 日志。"""
        return bool(self.get("db_debug", False))

    @property
    def qq_markdown_enabled(self) -> bool:
        """是否以 Markdown 发送帮助与市场订单（设置项「使用 Markdown 进行回复」）。

        键名保留 ``qq_markdown_enabled`` 以兼容老配置。作用范围（2026-11-16
        用户拍板：其余指令一律图片回复）：

        - 帮助消息（内联指令链接菜单依赖它，见 ``src/markdown/help.py``）；
        - 市场订单查询 WM（表格 + 序号取句按钮，见 ``src/markdown/market_orders.py``）。

        平台能不能渲染由 ``util.markdown_utils.MARKDOWN_CAPABLE_PLATFORMS``
        判定，两者合成最终发送方式（Markdown 或图片）。

        默认与 ``_conf_schema.json`` 一致为 ``False``（审查 P2-8：两处
        必须同值，schema 的默认值会被 AstrBot 落盘，代码回退值仅在
        键缺失时兜底，两者对立会造成语义混乱）。
        """
        return bool(self.get("qq_markdown_enabled", False))

    @property
    def wf_help_buttons(self) -> bool:
        """帮助消息是否附带可点击按钮。

        QQ 官方机器人的内联键盘属于独立权限，与 Markdown 权限分开开通；
        被平台拒绝时关掉此项即可回到「只有文本 / 图片」的帮助。
        """
        return bool(self.get("wf_help_buttons", True))

    @property
    def wf_help_inline_links(self) -> bool:
        """帮助 Markdown 是否使用内联指令链接菜单。

        菜单项是 ``mqqapi://aio/inlinecmd`` 客户端链接（同类 QQ 机器人
        验证过的成熟做法）：点击后把指令填入发送框，不依赖内联键盘权限；
        若平台拒绝含链接的消息，关闭此项回退为纯文本列表。
        """
        return bool(self.get("wf_help_inline_links", True))

    @property
    def wf_whisper_buttons(self) -> bool:
        """市场订单卡片是否附带序号取句按钮（与帮助按钮互相独立）。

        WM 的 Markdown 表格下方按钮：点击回复对应表格行号的私聊语句，
        长按复制进游戏；此前复用 ``wf_help_buttons``，2026-11-16 评审
        指出语义耦合后拆分为独立开关。
        """
        return bool(self.get("wf_whisper_buttons", True))

    @property
    def wf_help_logo_url(self) -> str:
        """帮助消息顶部的项目图标 URL；空串表示不带图标。

        QQ 官方 Markdown 的图片只支持公网 URL（开放平台会下载转存），
        本地文件路径无效；默认取插件仓库内 logo 的 jsDelivr 地址。
        """
        return str(self.get("wf_help_logo_url", "")).strip()

    @property
    def wf_help_logo_size(self) -> str:
        """顶部图片的显示尺寸（「宽x高」，如 256x256）。

        QQ 按 ``#宽px #高px`` 固定框显示图片，比例不一致会被居中裁切；
        大小不设上限（实测 256x256 正常）。默认 ``256x256`` 对应方形
        ``logo.png``（512x512 二倍图）。
        """
        return str(self.get("wf_help_logo_size", "256x256")).strip()

    @property
    def card_theme(self) -> str:
        """图片样式模式（dark / light）。"""
        from ..render.theme import DEFAULT_MODE, normalize_mode

        return normalize_mode(self._config.get("wf_card_theme"), DEFAULT_MODE)

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


def reload_plugin_config() -> PluginConfig:
    """重新读取配置文件，返回刷新后的单例。

    Web 设置页保存后调用，让 ``get_xxx()`` 这类读取立即看到新值；
    启动期读取的配置项仍需重载插件才会生效。
    """
    config = _get_default_config()
    config.reload()
    logger.debug("插件配置已重新加载")
    return config


def get_data_init_mode() -> str:
    """获取数据初始化模式（auto / always / never / offline）。"""
    return _get_default_config().wf_data_init_mode


def normalize_data_init_mode(mode: str | None) -> str:
    """规整外部传入的初始化模式，未知值回退 ``auto``。"""
    normalized = str(mode).strip().lower() if mode else ""
    return normalized if normalized in _DATA_INIT_MODES else DATA_INIT_MODE_AUTO


def get_wf_notification_retention_hours() -> int:
    """获取通知历史保留时长（小时）。"""
    return _get_default_config().wf_notification_retention_hours


def get_wf_data_source_cdn() -> str:
    """获取数据源CDN地址。"""
    return _get_default_config().wf_data_source_cdn


def get_wf_command_prefix() -> str:
    """获取Warframe 助手指令前缀，为空时指令无需前缀即可触发。"""
    return _get_default_config().wf_command_prefix


def get_db_debug() -> bool:
    """获取数据库调试模式开关。"""
    return _get_default_config().db_debug


def get_qq_markdown_enabled() -> bool:
    """获取 QQ 官方机器人 Markdown 消息格式开关。"""
    return _get_default_config().qq_markdown_enabled


def get_wf_help_buttons() -> bool:
    """获取帮助消息是否附带可点击按钮。"""
    return _get_default_config().wf_help_buttons


def get_wf_help_inline_links() -> bool:
    """获取帮助菜单是否使用 mqqapi 内联指令链接。"""
    return _get_default_config().wf_help_inline_links


def get_wf_whisper_buttons() -> bool:
    """获取市场订单卡片是否附带序号取句按钮。"""
    return _get_default_config().wf_whisper_buttons


def get_wf_help_logo_url() -> str:
    """获取帮助消息顶部的项目图标 URL（空串 = 不带图标）。"""
    return _get_default_config().wf_help_logo_url


def get_wf_help_logo_size() -> str:
    """获取帮助顶部图片的显示尺寸（「宽x高」）。"""
    return _get_default_config().wf_help_logo_size
