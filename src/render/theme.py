"""Card theme / 卡片主题

图片渲染的主体配色**只有一处来源**：:data:`THEME_MANAGER`。
任何卡片、组件、图标都通过它取当前主题，不允许各自持有色值。

三层结构
--------
``Palette``  19 个语义色字段（``canvas`` / ``surface`` / ``text`` / ``gold`` …）。
``Theme``    名字 + 一套 Palette，内置 ``dark`` / ``light`` 两套默认主题。
``ThemeManager`` 解析「配置 → 当前主题」，并缓存结果。

两种模式
--------
========  ==================================================
``dark``  默认。暗色，贴近游戏内 UI。
``light`` 亮色，适合白天或浅色聊天背景。
========  ==================================================

配置只有一项（``_conf_schema.json``）::

    wf_card_theme = "dark" | "light"

非法值（拼写错误、空值、旧版本残留的 ``custom``）统一回退默认的 ``dark``，
不会让渲染失败——群里的一张图不值得因为一个错别字崩掉。

旧卡片的迁移
------------
历史卡片用的是 ``draw_constant.ThemeColor`` 常量。``ThemeColor`` 已改为
主题代理（见该模块），所以**未迁移的卡片也会跟随当前主题**，只是版式仍是旧的。
"""
from __future__ import annotations

from typing import Any, Mapping

try:
    from astrbot.api import logger
except ImportError:  # 离线渲染 / 单测环境没有 AstrBot
    import logging

    logger = logging.getLogger(__name__)

from .design import Theme, get_theme

#: 允许的主题模式。
MODES: tuple[str, ...] = ("dark", "light")

#: 默认模式。
DEFAULT_MODE = "dark"

#: 旧常量名 → Palette 字段。``ThemeColor`` 的元类用它做动态取值。
LEGACY_FIELDS: Mapping[str, str] = {
    "BG_DARK": "canvas",
    "BG_CARD": "surface",
    "BG_CARD_ALT": "surface_alt",
    "DIVIDER": "border",
    "TEXT_PRIMARY": "text",
    "TEXT_SECONDARY": "text_muted",
    "TEXT_MUTED": "text_dim",
    "ACCENT": "gold",
    "ACCENT_GOLD": "gold",
    "ACCENT_BLUE": "blue",
    "ACCENT_GREEN": "green",
    "SUCCESS": "green",
    "WARNING": "amber",
    "DANGER": "red",
    "INFO": "blue",
    "REWARD_BG": "surface_alt",
    "TABLE_HEADER_BG": "surface_alt",
    "TABLE_EVEN_ROW": "surface",
    "TABLE_BORDER": "border",
    "CYCLE_WARM": "amber",
    "CYCLE_COLD": "blue",
}


def normalize_mode(value: Any, fallback: str = DEFAULT_MODE) -> str:
    """把配置值收敛到合法模式。"""
    text = str(value or "").strip().lower()
    return text if text in MODES else fallback


def build_theme(mode: str = DEFAULT_MODE) -> Theme:
    """解析出主题，不写缓存（纯函数，便于测试）。"""
    return get_theme(normalize_mode(mode))


class ThemeManager:
    """当前主题的持有者与唯一入口。"""

    def __init__(self) -> None:
        self._mode: str = DEFAULT_MODE
        self._theme: Theme = get_theme(DEFAULT_MODE)

    # ------------------------------------------------------------ 读

    @property
    def theme(self) -> Theme:
        """当前主题（绘制时取它，不要在卡片里缓存）。"""
        return self._theme

    @property
    def mode(self) -> str:
        return self._mode

    # ------------------------------------------------------------ 写

    def configure(self, mode: str = DEFAULT_MODE) -> Theme:
        """设置主题并返回结果。调用方：插件初始化 / 配置变更 / 测试。"""
        self._mode = normalize_mode(mode)
        self._theme = build_theme(self._mode)
        logger.debug(f"卡片主题已切换: {self._mode}")
        return self._theme

    def configure_from_config(self, config: Any) -> Theme:
        """从 AstrBot 配置读取模式。

        兼容三种输入：``AstrBotConfig``（dict-like）、普通 dict、``None``。
        """
        data = config or {}
        mode = data.get("wf_card_theme", DEFAULT_MODE) if hasattr(data, "get") else DEFAULT_MODE
        return self.configure(mode)

    def reset(self) -> Theme:
        """恢复默认（测试用）。"""
        return self.configure(DEFAULT_MODE)


#: 全局主题管理器。渲染层统一从这里取当前主题。
THEME_MANAGER = ThemeManager()


def current_theme() -> Theme:
    """快捷方法：当前主题。"""
    return THEME_MANAGER.theme


def apply_plugin_config(config: Any) -> Theme:
    """插件初始化时调用，把配置应用到全局主题。"""
    return THEME_MANAGER.configure_from_config(config)
