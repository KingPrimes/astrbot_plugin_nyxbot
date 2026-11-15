"""Branding / 品牌设置（署名 + 看板娘）

渲染路径需要同一份「署名文案」和「看板娘开关」——由 ``card_frame`` 的
页脚与看板娘绘制统一消费（审查 P2-7：旧路径 ``ImageCombiner.draw_card_footer``
已随无调用删除）。

因此这些值既不能写死在 :class:`DrawConstant`（现在是 ``Final`` 常量），
也不适合塞进 ``_conf_schema.json``（插件配置只保留主题切换）。折中做法：

* 文件放在插件数据目录（``render_branding.json``），由 :func:`save_branding` 写入；
* 读取带 mtime 缓存，绘制热路径不会反复读盘；
* 文件缺失 / 损坏 / 字段非法时，逐项回退到内置默认值，不影响渲染。

文件结构::

    {
      "signature": {"text": "Posted by: KingPrimes", "enabled": true},
      "standing":  {"enabled": true, "seasonal": true, "size": "md"}
    }
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from astrbot.api import logger

#: 品牌设置文件名（插件数据目录）。
BRANDING_FILENAME = "render_branding.json"

#: 看板娘尺寸档位 → (最大宽, 最大高)。**全仓唯一定义**（standing / card_frame
#: 均从这里取，审查 P2-2）。
STANDING_SIZES: dict[str, tuple[int, int]] = {
    "sm": (200, 300),
    "md": (280, 420),
    "lg": (360, 540),
}

#: 兜底署名文案。与 ``DrawConstant.FOOTER_TEXT`` 保持一致，避免两套文案。
DEFAULT_SIGNATURE = "Posted by: KingPrimes"

#: 内置默认值（深拷贝模板，调用方拿到的是副本）。
DEFAULT_BRANDING: dict[str, Any] = {
    "signature": {"text": DEFAULT_SIGNATURE, "enabled": True},
    "standing": {"enabled": True, "seasonal": True, "size": "md"},
}

#: mtime 缓存：(路径, mtime_ns, size) → 已归一化的配置
_cache: tuple[tuple[str, int, int], dict[str, Any]] | None = None

#: 路径缓存。热路径（署名/看板娘）每张卡会取多次，路径在进程内不变，
#: 首次计算后固定，避免每次都走 data_path → plugin_name 一层。
_BRANDING_PATH: Path | None = None


def branding_path() -> Path:
    """品牌设置文件路径（插件数据目录）。"""
    global _BRANDING_PATH

    if _BRANDING_PATH is None:
        from ..util.data_path import get_public_data_path

        _BRANDING_PATH = Path(get_public_data_path()) / BRANDING_FILENAME
    return _BRANDING_PATH


def _as_bool(value: Any, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes", "on", "是", "开"}:
            return True
        if text in {"0", "false", "no", "off", "否", "关"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return fallback


def normalize_branding(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """把任意输入收敛成合法品牌设置。非法字段逐项回退，不抛异常。"""
    result = {
        "signature": dict(DEFAULT_BRANDING["signature"]),
        "standing": dict(DEFAULT_BRANDING["standing"]),
    }
    if not isinstance(payload, Mapping):
        return result

    signature = payload.get("signature")
    if isinstance(signature, Mapping):
        text = signature.get("text")
        if isinstance(text, str) and text.strip():
            result["signature"]["text"] = text.strip()
        result["signature"]["enabled"] = _as_bool(
            signature.get("enabled"), result["signature"]["enabled"]
        )

    standing = payload.get("standing")
    if isinstance(standing, Mapping):
        result["standing"]["enabled"] = _as_bool(
            standing.get("enabled"), result["standing"]["enabled"]
        )
        result["standing"]["seasonal"] = _as_bool(
            standing.get("seasonal"), result["standing"]["seasonal"]
        )
        size = str(standing.get("size", "")).strip().lower()
        if size in STANDING_SIZES:
            result["standing"]["size"] = size

    return result


def load_branding() -> dict[str, Any]:
    """读取品牌设置（带 mtime 缓存；文件缺失返回默认值）。

    返回缓存 dict 的**深拷贝**（审查 P2-12）：调用方误改返回值不会污染
    全局缓存。配置很小，深拷贝开销可忽略。
    """
    global _cache

    path = branding_path()
    try:
        stat = path.stat()
    except OSError:
        return normalize_branding(None)

    key = (str(path), stat.st_mtime_ns, stat.st_size)
    if _cache is not None and _cache[0] == key:
        return deepcopy(_cache[1])

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning(f"品牌设置读取失败（{path}）：{exc}")
        payload = None

    resolved = normalize_branding(payload if isinstance(payload, Mapping) else None)
    _cache = (key, resolved)
    return deepcopy(resolved)


def save_branding(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """保存品牌设置并返回落盘后的归一化结果（当前无页面入口，供脚本或后续接口调用）。"""
    global _cache

    resolved = normalize_branding(payload if isinstance(payload, Mapping) else None)
    path = branding_path()
    path.write_text(json.dumps(resolved, ensure_ascii=False, indent=2), encoding="utf-8")
    _cache = None  # 强制下次重新读盘
    return resolved


def reset_cache() -> None:
    """清缓存（测试用）。"""
    global _cache, _BRANDING_PATH
    _cache = None
    _BRANDING_PATH = None


def signature_text() -> str:
    """当前署名的**实际文本**（关闭时返回空串）。"""
    signature = load_branding()["signature"]
    return signature["text"] if signature["enabled"] else ""


def standing_enabled() -> bool:
    """看板娘是否全局启用。"""
    return bool(load_branding()["standing"]["enabled"])


def standing_seasonal() -> bool:
    """看板娘是否跟随季节。"""
    return bool(load_branding()["standing"]["seasonal"])


def standing_size() -> tuple[int, int]:
    """看板娘默认尺寸档位对应的 (max_w, max_h)。"""
    size = load_branding()["standing"]["size"]
    return STANDING_SIZES.get(size, STANDING_SIZES["md"])
