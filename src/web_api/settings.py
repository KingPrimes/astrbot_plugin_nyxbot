"""Plugin settings API — Plugin Pages 后端

把 ``_conf_schema.json`` 暴露成可读可写的接口，供数据管理页的「插件设置」使用：

- ``GET  /<plugin>/config``  返回配置项元信息（类型 / 选项 / 分组 / 是否需重载）+ 当前值
- ``POST /<plugin>/config``  校验后写入插件配置（优先走 AstrBotConfig，回退写配置文件）
- ``GET  /<plugin>/i18n``    返回页面可用语言与文案，供前端做语言同步与英文回退

写入后同步刷新 ``PluginConfig`` 单例，使 ``get_xxx()`` 这类读取立即拿到新值；
标注 ``requires_reload`` 的项（启动期读取）仍需重载插件才会生效。
"""
from __future__ import annotations

import inspect
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import orjson

from astrbot.api import logger
from astrbot.api.star import Context
from astrbot.core.utils.astrbot_path import get_astrbot_config_path

from ..config.config import reload_plugin_config
from ..util import get_plugin_name

_PLUGIN_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_PATH = _PLUGIN_ROOT / "_conf_schema.json"
_I18N_DIR = _PLUGIN_ROOT / ".astrbot-plugin" / "i18n"
_PAGE_KEY = "nyxbot-admin"

#: 分组顺序：与页面上的展示顺序一致，未列出的键归入 ``other``。
CONFIG_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("command", ("wf_command_prefix",)),
    ("data", ("wf_data_init_mode", "wf_data_source_cdn", "wf_update_interval")),
    ("render", ("wf_card_theme",)),
    ("notify", ("wf_notification_retention_hours", "qq_markdown_enabled")),
    ("debug", ("db_debug",)),
)

#: 只在启动 / 注册期读取，改完必须重载插件。
RELOAD_KEYS = frozenset({
    "wf_card_theme",
    "wf_command_prefix",
    "wf_data_init_mode",
    "wf_update_interval",
    "db_debug",
})

#: 数值型配置的取值范围（(最小, 最大)），前端据此做输入限制。
CONFIG_LIMITS: dict[str, tuple[int | None, int | None]] = {
    "wf_update_interval": (60, 86400),
    "wf_notification_retention_hours": (1, 720),
}

#: 允许通过本接口读写的类型；file / list / dict 等交给 AstrBot 原生面板。
_SUPPORTED_TYPES = frozenset({"string", "text", "int", "float", "bool"})

_GROUP_OF: dict[str, str] = {
    key: group for group, keys in CONFIG_GROUPS for key in keys
}
_GROUP_ORDER: dict[str, int] = {
    group: index for index, (group, _keys) in enumerate(CONFIG_GROUPS)
}


def _load_schema() -> dict[str, Any]:
    """读取配置模板；文件缺失或损坏时返回空 schema。"""
    try:
        if _SCHEMA_PATH.is_file():
            return orjson.loads(_SCHEMA_PATH.read_text(encoding="utf-8-sig"))
    except Exception as exc:  # noqa: BLE001 - 配置模板损坏不应拖垮页面
        logger.warning(f"读取 _conf_schema.json 失败: {exc}")
    return {}


def _config_file_path() -> Path:
    """插件配置文件路径（与 ``PluginConfig`` 保持一致）。"""
    return Path(get_astrbot_config_path()) / f"{get_plugin_name()}_config.json"


def _current_values(schema: dict[str, Any], config: Any) -> dict[str, Any]:
    """合并配置文件当前值与 schema 默认值。"""
    values: dict[str, Any] = {}
    for key, item in schema.items():
        if not isinstance(item, dict):
            continue
        value = None
        if config is not None:
            try:
                value = config.get(key) if hasattr(config, "get") else config[key]
            except Exception:  # noqa: BLE001 - 单个键读取失败不影响整体
                value = None
        values[key] = item.get("default") if value is None else value
    return values


def _group_of(key: str) -> str:
    """配置项所属分组。"""
    return _GROUP_OF.get(key, "other")


def _coerce(key: str, item: dict[str, Any], raw: Any) -> tuple[Any, str | None]:
    """按 schema 校验并转换单个配置值。

    Returns:
        ``(值, 错误信息)``；校验失败时值为 ``None``，错误信息为英文键名，
        前端用 i18n 映射成对应语言的提示。
    """
    item_type = str(item.get("type", "string"))
    options = [str(option) for option in item.get("options") or []]

    if item_type == "bool":
        if isinstance(raw, bool):
            return raw, None
        if isinstance(raw, str) and raw.strip().lower() in {"true", "false", "1", "0"}:
            return raw.strip().lower() in {"true", "1"}, None
        return None, "invalid_bool"

    if item_type in {"int", "float"}:
        try:
            number = int(raw) if item_type == "int" else float(raw)
        except (TypeError, ValueError):
            return None, "invalid_number"
        low, high = CONFIG_LIMITS.get(key, (None, None))
        if low is not None and number < low:
            return None, f"min:{low}"
        if high is not None and number > high:
            return None, f"max:{high}"
        return number, None

    # string / text
    text = "" if raw is None else str(raw)
    if item_type == "text":
        return text, None
    text = text.strip()
    if options and text not in options:
        return None, "invalid_option"
    if len(text) > 2048:
        return None, "too_long"
    if key == "wf_command_prefix" and not _COMMAND_PREFIX_RE.match(text):
        return None, "invalid_prefix"
    return text, None


#: 指令前缀字符集：字母 / 数字 / 下划线，0~16 位（空串 = 无前缀）。
#: 含空格、斜杠或中文会破坏 ``filter.command_group(prefix)`` 的指令注册，
#: 表现为「保存成功但插件重载后指令全部失效」。
_COMMAND_PREFIX_RE = re.compile(r"^[A-Za-z0-9_]{0,16}$")


def _write_config_file(values: dict[str, Any]) -> None:
    """没有 AstrBotConfig 时直接改配置文件（保留其它未知键）。

    审查 P1-4：配置文件是插件设置的唯一持久化载体，直接覆盖写盘一旦
    中途断电 / 崩溃，会留下截断的 JSON，下次启动解析失败、配置全丢。
    改为「同目录临时文件 + fsync + ``os.replace``」原子替换，
    任何时刻磁盘上都有一份完整配置。
    """
    path = _config_file_path()
    data: dict[str, Any] = {}
    if path.is_file():
        try:
            data = orjson.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"配置文件解析失败: {exc}") from exc
    data.update(values)

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = orjson.dumps(
        data, option=orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS
    ).decode()

    tmp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            tmp_name = tmp.name
            tmp.write(payload)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp_name, path)  # 同目录替换是原子操作（POSIX rename / Windows ReplaceFile）
        tmp_name = None
    finally:
        if tmp_name is not None:  # replace 失败时清理残留临时文件
            Path(tmp_name).unlink(missing_ok=True)


async def _persist(config: Any, values: dict[str, Any]) -> None:
    """写入内存配置并落盘，随后刷新 PluginConfig 单例。"""
    if config is not None:
        for key, value in values.items():
            try:
                config[key] = value
            except Exception as exc:  # noqa: BLE001 - 只读配置对象
                raise RuntimeError(f"配置项 {key} 不可写: {exc}") from exc

    save = getattr(config, "save_config", None)
    if callable(save):
        result = save()
        if inspect.isawaitable(result):
            await result
    else:
        _write_config_file(values)

    reload_plugin_config()


def register_settings_apis(context: Context, config: Any = None) -> None:
    """注册插件设置相关 Web API。

    Args:
        context: AstrBot 上下文实例。
        config: 插件持有的 ``AstrBotConfig``；为 ``None`` 时退化为直接读写配置文件。
    """
    plugin = get_plugin_name() or "astrbot_plugin_nyxbot"

    # ------------------------------------------------------------------ 读取
    async def get_config():
        """返回配置项元信息与当前值。"""
        from quart import jsonify

        schema = _load_schema()
        items: list[dict[str, Any]] = []
        for key, item in schema.items():
            if not isinstance(item, dict):
                continue
            item_type = str(item.get("type", "string")).lower()
            if item_type not in _SUPPORTED_TYPES:
                continue
            low, high = CONFIG_LIMITS.get(key, (None, None))
            options = item.get("options") or []
            items.append({
                "key": key,
                "type": item_type,
                "group": _group_of(key),
                "label": item.get("description") or key,
                "hint": item.get("hint") or "",
                "default": item.get("default"),
                "options": [str(option) for option in options],
                "requires_reload": key in RELOAD_KEYS,
                "min": low,
                "max": high,
            })

        items.sort(key=lambda entry: (
            _GROUP_ORDER.get(entry["group"], len(_GROUP_ORDER)),
            list(schema).index(entry["key"]),
        ))
        return jsonify({"items": items, "values": _current_values(schema, config)})

    context.register_web_api(
        f"/{plugin}/config",
        get_config,
        ["GET"],
        "读取插件配置项与当前值",
    )

    # ------------------------------------------------------------------ 写入
    async def update_config():
        """校验并保存配置项。"""
        from quart import jsonify, request

        payload = await request.get_json(silent=True) or {}
        values = payload.get("values")
        if not isinstance(values, dict):
            return jsonify({"success": False, "error": "values must be an object"}), 400

        schema = _load_schema()
        before = _current_values(schema, config)
        cleaned: dict[str, Any] = {}
        errors: dict[str, str] = {}

        for key, raw in values.items():
            item = schema.get(key)
            if not isinstance(item, dict):
                errors[key] = "unknown_key"
                continue
            value, error = _coerce(key, item, raw)
            if error:
                errors[key] = error
            else:
                cleaned[key] = value

        if errors:
            # 字段级校验失败用 200 + success=false：Plugin Pages 的 bridge 对
            # 非 2xx 只抛出错误文本，拿不到 errors 明细，页面就无法高亮具体项。
            return jsonify({"success": False, "errors": errors})

        try:
            await _persist(config, cleaned)
        except Exception as exc:  # noqa: BLE001 - 写盘失败要回给页面
            logger.error(f"保存插件配置失败: {exc}", exc_info=True)
            return jsonify({"success": False, "error": str(exc)}), 500

        changed = [key for key, value in cleaned.items() if before.get(key) != value]
        reload_keys = [key for key in changed if key in RELOAD_KEYS]
        if changed:
            logger.info(f"插件配置已更新: {', '.join(changed)}")

        return jsonify({
            "success": True,
            "values": _current_values(schema, config),
            "changed": changed,
            "reload_keys": reload_keys,
        })

    context.register_web_api(
        f"/{plugin}/config/update",
        update_config,
        ["POST"],
        "保存插件配置项",
    )

    # ------------------------------------------------------------------ 多语言
    async def get_i18n():
        """返回页面可选语言与文案。

        只返回本视图（``nyxbot-admin``）的文案；语言列表来自 i18n 目录，
        前端据此判断 AstrBot 当前语言是否有对应文件，没有就回退英文。
        """
        from quart import jsonify

        pages: dict[str, Any] = {}
        if _I18N_DIR.is_dir():
            for path in sorted(_I18N_DIR.glob("*.json")):
                try:
                    data = orjson.loads(path.read_text(encoding="utf-8-sig"))
                except Exception as exc:  # noqa: BLE001 - 单个语言文件坏了不拖垮页面
                    logger.warning(f"读取语言文件 {path.name} 失败: {exc}")
                    continue
                page = (data.get("pages") or {}).get(_PAGE_KEY)
                if isinstance(page, dict) and page:
                    pages[path.stem] = page

        locales = sorted(pages)
        fallback = "en" if "en" in pages else (locales[0] if locales else "en")
        return jsonify({"locales": locales, "fallback": fallback, "pages": pages})

    context.register_web_api(
        f"/{plugin}/i18n",
        get_i18n,
        ["GET"],
        "读取页面多语言文案",
    )
