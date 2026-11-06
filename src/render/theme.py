"""Card theme / 卡片主题

图片渲染的主体配色**只有一处来源**：:data:`THEME_MANAGER`。
任何卡片、组件、图标都通过它取当前主题，不允许各自持有色值。

三层结构
--------
``Palette``  19 个语义色字段（``canvas`` / ``surface`` / ``text`` / ``gold`` …）。
``Theme``    名字 + 一套 Palette，内置 ``dark`` / ``light`` 两套默认主题。
``ThemeManager`` 解析「配置 → 当前主题」，并缓存结果。

三种模式
--------
========  ==================================================
``dark``  默认。深色，贴近游戏内 UI。
``light`` 浅色，适合白天或浅色聊天背景。
``custom`` 选一套 base（dark/light）再按字段覆盖，只认 ``#RRGGBB``。
========  ==================================================

配置只有一项（``_conf_schema.json``）::

    wf_card_theme = "dark" | "light" | "custom"

``custom`` 的配色**不进插件配置**，而是由渲染工作台写到数据目录的
``render_theme.json``（见 :func:`load_custom_theme` / :func:`save_custom_theme`）::

    {"base": "dark", "colors": {"surface": "#101522", "gold": "#FFC83D"}}

未生成该文件时，``custom`` 等同 ``dark``。

非法值（拼写错误、非 ``#RRGGBB``、未知字段）逐条忽略并回退底稿，
不会让渲染失败——群里的一张图不值得因为一个错别字崩掉。

旧卡片的迁移
------------
历史卡片用的是 ``draw_constant.ThemeColor`` 常量。``ThemeColor`` 已改为
主题代理（见该模块），所以**未迁移的卡片也会跟随当前主题**，只是版式仍是旧的。
"""
from __future__ import annotations

import json
from dataclasses import fields, replace
from pathlib import Path
from typing import Any, Mapping

try:
    from astrbot.api import logger
except ImportError:  # 离线渲染 / 单测环境没有 AstrBot
    import logging

    logger = logging.getLogger(__name__)

from .design import RGB, Palette, Theme, get_theme

#: 允许的主题模式。
MODES: tuple[str, ...] = ("dark", "light", "custom")

#: 默认模式。
DEFAULT_MODE = "dark"

#: ``custom`` 模式可选底稿（= 内置主题名）。
BASE_MODES: tuple[str, ...] = ("dark", "light")

#: 自定义主题可覆盖的字段（顺序即配置视图顺序）。其余字段沿用底稿。
CUSTOM_FIELDS: tuple[str, ...] = (
    "canvas",
    "surface",
    "surface_alt",
    "border",
    "text",
    "text_muted",
    "text_dim",
    "gold",
    "blue",
    "green",
    "amber",
    "red",
)

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


def parse_color(value: Any) -> RGB | None:
    """把配置里的颜色解析成 RGB；非法值返回 ``None``。

    接受 ``#RRGGBB`` / ``RRGGBB``，大小写不限；其余一律视为未设置。
    """
    if not isinstance(value, str):
        return None
    text = value.strip().lstrip("#")
    if len(text) != 6:
        return None
    try:
        return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)
    except ValueError:
        return None


def normalize_mode(value: Any, fallback: str = DEFAULT_MODE) -> str:
    """把配置值收敛到合法模式。"""
    text = str(value or "").strip().lower()
    return text if text in MODES else fallback


def build_theme(
    mode: str = DEFAULT_MODE,
    base: str = DEFAULT_MODE,
    colors: Mapping[str, Any] | None = None,
) -> Theme:
    """解析出主题，不写缓存（纯函数，便于测试）。

    Args:
        mode: ``dark`` / ``light`` / ``custom``。
        base: ``custom`` 模式的底稿，``dark`` 或 ``light``。
        colors: 字段 → 颜色字符串；仅 ``custom`` 生效，非法项忽略。

    Returns:
        :class:`design.Theme`；``custom`` 时 ``name`` 为 ``custom``。
    """
    resolved_mode = normalize_mode(mode)

    if resolved_mode != "custom":
        return get_theme(resolved_mode)

    base_name = normalize_mode(base, DEFAULT_MODE)
    if base_name == "custom":  # base 不允许递归
        base_name = DEFAULT_MODE

    base_palette: Palette = get_theme(base_name).palette
    overrides: dict[str, RGB] = {}
    for key, raw in (colors or {}).items():
        field = str(key).strip()
        if field == "base":  # 底稿是元字段，不是色板字段
            continue
        if field not in {item.name for item in fields(Palette)}:
            logger.warning(f"自定义主题：未知字段 {field!r}，已忽略")
            continue
        rgb = parse_color(raw)
        if rgb is None:
            if str(raw).strip():
                logger.warning(f"自定义主题：{field}={raw!r} 不是 #RRGGBB，已忽略")
            continue
        overrides[field] = rgb

    palette = replace(base_palette, **overrides) if overrides else base_palette
    return Theme("custom", palette)


#: 自定义主题文件名（位于插件数据目录，由工作台读写）。
CUSTOM_THEME_FILENAME = "render_theme.json"


def custom_theme_path() -> Path:
    """自定义主题文件路径（插件数据目录下）。"""
    from ..util.data_path import get_public_data_path

    return Path(get_public_data_path()) / CUSTOM_THEME_FILENAME


def load_custom_theme() -> dict[str, Any]:
    """读取工作台保存的自定义主题；缺失或损坏时返回空 dict。"""
    path = custom_theme_path()
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning(f"自定义主题读取失败（{path}）：{exc}")
        return {}
    return payload if isinstance(payload, dict) else {}


def save_custom_theme(payload: Mapping[str, Any]) -> Path:
    """保存自定义主题（工作台写入入口）。返回落盘路径。"""
    path = custom_theme_path()
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


class ThemeManager:
    """当前主题的持有者与唯一入口。"""

    def __init__(self) -> None:
        self._mode: str = DEFAULT_MODE
        self._base: str = DEFAULT_MODE
        self._overrides: dict[str, RGB] = {}
        self._theme: Theme = get_theme(DEFAULT_MODE)

    # ------------------------------------------------------------ 读

    @property
    def theme(self) -> Theme:
        """当前主题（绘制时取它，不要在卡片里缓存）。"""
        return self._theme

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def base(self) -> str:
        return self._base

    @property
    def overrides(self) -> Mapping[str, RGB]:
        return dict(self._overrides)

    # ------------------------------------------------------------ 写

    def configure(
        self,
        mode: str = DEFAULT_MODE,
        base: str = DEFAULT_MODE,
        colors: Mapping[str, Any] | None = None,
    ) -> Theme:
        """设置主题并返回结果。调用方：插件初始化 / 配置变更 / 测试。"""
        self._mode = normalize_mode(mode)
        self._base = normalize_mode(base, DEFAULT_MODE)
        if self._base == "custom":
            self._base = DEFAULT_MODE
        self._theme = build_theme(self._mode, self._base, colors)
        self._overrides = {
            item.name: getattr(self._theme.palette, item.name)
            for item in fields(Palette)
            if self._mode == "custom"
            and item.name in CUSTOM_FIELDS
            and getattr(self._theme.palette, item.name)
            != getattr(get_theme(self._base).palette, item.name)
        }
        logger.debug(f"卡片主题已切换: {self._mode}（base={self._base}，覆盖 {len(self._overrides)} 项）")
        return self._theme

    def configure_from_config(self, config: Any) -> Theme:
        """从 AstrBot 配置读取模式；``custom`` 的配色另从数据目录读。

        兼容三种输入：``AstrBotConfig``（dict-like）、普通 dict、``None``。
        """
        data = config or {}
        mode = data.get("wf_card_theme", DEFAULT_MODE) if hasattr(data, "get") else DEFAULT_MODE

        if normalize_mode(mode) != "custom":
            return self.configure(mode)

        payload = load_custom_theme()
        base = payload.get("base", DEFAULT_MODE)
        colors = payload.get("colors")
        if not isinstance(colors, Mapping):
            colors = {key: value for key, value in payload.items() if key != "base"}
        return self.configure("custom", base, colors)

    def reset(self) -> Theme:
        """恢复默认（测试用）。"""
        return self.configure(DEFAULT_MODE, DEFAULT_MODE, {})


#: 全局主题管理器。渲染层统一从这里取当前主题。
THEME_MANAGER = ThemeManager()


def current_theme() -> Theme:
    """快捷方法：当前主题。"""
    return THEME_MANAGER.theme


def apply_plugin_config(config: Any) -> Theme:
    """插件初始化时调用，把配置应用到全局主题。"""
    return THEME_MANAGER.configure_from_config(config)
