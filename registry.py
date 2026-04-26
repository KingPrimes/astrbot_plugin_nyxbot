"""Command registry with module path patching for AstrBot plugin handler discovery.

AstrBot's PluginManager discovers handlers by matching handler_module_path
against the main plugin module path (data.plugins.astrbot_plugin_nyxbot.main).
Handlers defined in separate files have a different __module__, so they won't
be discovered. This module provides decorators that patch __module__ to ensure
discovery works correctly.

AstrBot 插件管理器通过匹配 handler_module_path 与主插件模块路径来发现 Handler。
在独立文件中定义的 Handler 具有不同的 __module__，因此无法被发现。
本模块提供修补 __module__ 的装饰器，确保发现机制正常工作。

支持通过 wf_command_prefix 配置项自定义指令前缀：
- 前缀非空时（如 "wf"）：指令以 /wf help 形式触发
- 前缀为空时（默认）：指令以 /help 形式触发，无需前缀
"""

from __future__ import annotations

import json
import os

from astrbot.api.event import filter

MAIN_MODULE = "data.plugins.astrbot_plugin_nyxbot.main"


def _patch_module(func):
    """Patch function's __module__ to the main module path.

    修补函数的 __module__ 为主模块路径，确保 Handler 可被 PluginManager 发现。
    """
    func.__module__ = MAIN_MODULE
    return func


def _load_prefix_from_config() -> str:
    """Try to load wf_command_prefix from the plugin config file.

    尝试从插件配置文件中加载 wf_command_prefix。
    如果配置文件不存在或读取失败，返回默认值空字符串（无前缀）。
    """
    try:
        # Plugin dir: data/plugins/astrbot_plugin_nyxbot/
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        # AstrBot data dir: data/
        data_dir = os.path.dirname(os.path.dirname(plugin_dir))
        # Config dir: data/config/
        config_dir = os.path.join(data_dir, "config")
        plugin_name = os.path.basename(plugin_dir)
        config_path = os.path.join(config_dir, f"{plugin_name}_config.json")

        if os.path.exists(config_path):
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
            return str(config.get("wf_command_prefix", "")).strip()
    except Exception:
        pass
    return ""  # Default: no prefix


class _PatchedRegisteringCommandable:
    """Wraps RegisteringCommandable to auto-patch __module__ on sub-commands.

    封装 RegisteringCommandable，自动修补子指令的 __module__。
    用于前缀非空时，指令以 /<prefix> <sub_command> 形式触发。
    """

    def __init__(self, registering):
        self._registering = registering

    def command(self, name=None, alias=None, **kwargs):
        """Register a sub-command with module path patching.

        注册子指令并自动修补模块路径。
        """
        def decorator(func):
            _patch_module(func)
            return self._registering.command(name, alias=alias, **kwargs)(func)
        return decorator

    def group(self, name=None, alias=None, **kwargs):
        """Register a sub-command group with module path patching.

        注册子指令组并自动修补模块路径。
        """
        def decorator(func):
            _patch_module(func)
            result = self._registering.group(name, alias=alias, **kwargs)(func)
            return _PatchedRegisteringCommandable(result)
        return decorator

    def custom_filter(self, custom_type_filter, *args, **kwargs):
        """Register a custom filter with module path patching.

        注册自定义过滤器并自动修补模块路径。
        """
        def decorator(func):
            _patch_module(func)
            return self._registering.custom_filter(
                custom_type_filter, *args, **kwargs
            )(func)
        return decorator


class _PatchedTopLevelCommandable:
    """When prefix is empty, registers commands as top-level commands.

    当前缀为空时，将指令注册为顶级指令（无需前缀即可触发）。
    例如 /help 而非 /wf help。
    """

    def command(self, name=None, alias=None, **kwargs):
        """Register a top-level command with module path patching.

        注册顶级指令并自动修补模块路径。
        """
        def decorator(func):
            _patch_module(func)
            return filter.command(name, alias=alias, **kwargs)(func)
        return decorator

    def group(self, name=None, alias=None, **kwargs):
        """Register a top-level command group with module path patching.

        注册顶级指令组并自动修补模块路径。
        """
        def decorator(func):
            _patch_module(func)
            result = filter.command_group(name, alias=alias, **kwargs)(func)
            return _PatchedRegisteringCommandable(result)
        return decorator

    def custom_filter(self, custom_type_filter, *args, **kwargs):
        """Register a custom filter with module path patching.

        注册自定义过滤器并自动修补模块路径。
        """
        def decorator(func):
            _patch_module(func)
            return filter.custom_filter(
                custom_type_filter, *args, **kwargs
            )(func)
        return decorator


# --- Load command prefix from config / 从配置加载指令前缀 ---
command_prefix: str = _load_prefix_from_config()
"""当前指令前缀。为空表示无前缀，非空时作为指令组名。"""

# --- Command Groups / 指令组 ---

if command_prefix:
    # With prefix: use command group / 有前缀：使用指令组（如 /wf help）
    @_patch_module
    def _wf_group_handler(self):
        """Warframe 助手指令组"""
        pass

    wf = _PatchedRegisteringCommandable(
        filter.command_group(command_prefix)(_wf_group_handler)
    )
else:
    # No prefix: register as top-level commands / 无前缀：注册为顶级指令（如 /help）
    wf = _PatchedTopLevelCommandable()
