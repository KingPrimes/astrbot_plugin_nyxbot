# ==================================================================
# 获取 metadata.yaml 中的插件信息
# ==================================================================
from pathlib import Path

_METADATA_PATH = Path(__file__).resolve().parent.parent / "metadata.yaml"


def get_plugin_name() -> str:
    """获取当前插件的 name 属性（从 metadata.yaml 中读取）"""
    import yaml

    with open(_METADATA_PATH, "r", encoding="utf-8") as f:
        metadata = yaml.safe_load(f)
    return metadata.get("name", "")
