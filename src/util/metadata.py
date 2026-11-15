from __future__ import annotations

# ==================================================================
# 获取 metadata.yaml 中的插件信息
# ==================================================================
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_METADATA_PATH = Path(__file__).resolve().parents[2] / "metadata.yaml"


@lru_cache(maxsize=1)
def _load_metadata() -> dict[str, Any]:
    """读取 metadata.yaml 并缓存。

    插件元数据在进程生命周期内不变（热路径如品牌路径、配置路径、
    User-Agent 都会取它），解析一次即可，避免每次调用都读盘。
    """
    with open(_METADATA_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_plugin_name() -> str:
    """获取当前插件的 name 属性（从 metadata.yaml 中读取）"""
    return _load_metadata().get("name", "")


def get_plugin_version() -> str:
    """获取当前插件的 version 属性（从 metadata.yaml 中读取）。

    对齐 Go 的 ``version.Version``：用于 HTTP User-Agent 等对外标识。
    """
    return str(_load_metadata().get("version", "") or "")
