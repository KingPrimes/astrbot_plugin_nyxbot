from __future__ import annotations

# ==================================================================
# 获取 metadata.yaml 中的插件信息
# ==================================================================
from pathlib import Path

import yaml

_METADATA_PATH = Path(__file__).resolve().parents[2] / "metadata.yaml"


def get_plugin_name() -> str:
    """获取当前插件的 name 属性（从 metadata.yaml 中读取）"""
    with open(_METADATA_PATH, encoding="utf-8") as f:
        metadata = yaml.safe_load(f)
    return metadata.get("name", "")


def get_plugin_version() -> str:
    """获取当前插件的 version 属性（从 metadata.yaml 中读取）。

    对齐 Go 的 ``version.Version``：用于 HTTP User-Agent 等对外标识。
    """
    with open(_METADATA_PATH, encoding="utf-8") as f:
        metadata = yaml.safe_load(f)
    return str(metadata.get("version", "") or "")
