"""DataSource 版本跟踪 / DataSource version tracking

DataSource 仓库（``KingPrimes/DataSource``）以 tag 发布数据包，``warframe/`` 下是
各个 JSON 数据集。本模块负责回答一个问题：

    **这次启动，哪些数据集需要重新导入？**

做法：

1. 记录「本地已应用的 tag」到 ``<插件数据目录>/data_source_version.json``；
2. 启动时取远端最新 tag：
   - 与记录相同 → 什么都不用导；
   - 不同 → 调 GitHub compare 接口算出两个 tag 之间**实际变化**的文件，
     只导这几份；
   - compare 失败（限流 / tag 被删）→ 退化为全量，保证数据不缺。
3. 导入成功后写回新 tag。

这样「出现新版只更新对应的数据」，不必每次全量重拉。
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from astrbot.api import logger

from ..api.cdn_client import CdnClient
from ..util import fetch_json_with_retry
from ..util.data_path import get_public_data_path

STATE_FILE_NAME = "data_source_version.json"
COMPARE_URL = "https://api.github.com/repos/KingPrimes/DataSource/compare/{old}...{new}"
DATASET_PREFIX = "warframe/"

_COMPARE_FILE_LIMIT = 300
"""GitHub compare 接口单次返回的文件数上限；达到即视为被截断。"""


@dataclass(frozen=True)
class UpdatePlan:
    """本次启动的数据更新计划。

    Attributes:
        tag: 远端最新 tag（拿不到时为空串）。
        changed: 变化的文件名集合；``None`` 表示全量导入，空集表示无需导入。
    """

    tag: str
    changed: set[str] | None = field(default=None)

    @property
    def full(self) -> bool:
        """是否需要全量导入。"""
        return self.changed is None

    @property
    def empty(self) -> bool:
        """是否没有任何数据集需要更新。"""
        return self.changed is not None and not self.changed

    def needs(self, *file_names: str) -> bool:
        """判断给定数据集（``warframe/`` 下的文件名）是否需要导入。"""
        if self.changed is None:
            return True
        return any(f"{DATASET_PREFIX}{name}" in self.changed for name in file_names)


def _state_path() -> Path:
    return Path(get_public_data_path()) / STATE_FILE_NAME


def read_state() -> dict:
    """读取本地版本状态；文件缺失或损坏时返回空字典。"""
    try:
        raw = _state_path().read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except OSError as exc:
        logger.debug(f"读取 DataSource 版本状态失败: {exc}")
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("DataSource 版本状态文件损坏，按无状态处理")
        return {}
    return data if isinstance(data, dict) else {}


def write_state(tag: str) -> None:
    """记录已应用的 tag。"""
    if not tag:
        return
    payload = {"tag": tag, "updated_at": int(time.time())}
    try:
        _state_path().write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info(f"DataSource 版本状态已更新: {tag}")
    except OSError as exc:
        logger.warning(f"写入 DataSource 版本状态失败: {exc}")


async def compare_tags(old_tag: str, new_tag: str) -> set[str] | None:
    """用 GitHub compare 接口列出两个 tag 之间变化的文件。

    GitHub 的 compare 接口最多返回约 300 个文件；达到上限说明列表被截断，
    此时无法确定完整的变化集合，返回 ``None`` 让调用方退化为全量，
    否则会漏掉未列出的数据集并写错版本标记。

    Returns:
        变化的文件路径集合；无法获取或结果被截断时返回 ``None``。
    """
    url = COMPARE_URL.format(old=old_tag, new=new_tag)
    data = await fetch_json_with_retry(
        url,
        log_templates=None,
        max_retries=1,
    )
    if not isinstance(data, dict):
        return None
    files = data.get("files")
    if not isinstance(files, list):
        return None
    if len(files) >= _COMPARE_FILE_LIMIT:
        logger.warning(
            f"compare 返回 {len(files)} 个文件，疑似被截断，退化为全量导入"
        )
        return None
    changed = {
        str(item.get("filename"))
        for item in files
        if isinstance(item, dict) and item.get("filename")
    }
    return changed


async def plan_update() -> UpdatePlan:
    """计算本次启动需要导入哪些数据集。

    规则：
    - 无本地状态（首次运行）→ 全量；
    - 远端 tag 与本地一致 → 无需导入；
    - 不一致 → 只导入变化的文件；
    - 取不到远端 tag（离线/限流）→ 若有本地状态则跳过，否则全量。
    """
    state = read_state()
    applied = str(state.get("tag") or "")

    latest = await CdnClient.get_latest_tag()
    if not latest:
        if applied:
            logger.warning(
                f"取不到 DataSource 版本号，沿用本地数据（已应用 {applied}）"
            )
            return UpdatePlan(tag="", changed=set())
        logger.warning("取不到 DataSource 版本号，且无本地记录，按全量导入处理")
        return UpdatePlan(tag="", changed=None)

    if applied == latest:
        return UpdatePlan(tag=latest, changed=set())

    if not applied:
        logger.info(f"首次同步 DataSource {latest}，执行全量导入")
        return UpdatePlan(tag=latest, changed=None)

    changed = await compare_tags(applied, latest)
    if changed is None:
        logger.warning(
            f"无法比较 {applied} → {latest} 的差异（可能限流或 tag 已删），退化为全量导入"
        )
        return UpdatePlan(tag=latest, changed=None)

    dataset_changes = {p for p in changed if p.startswith(DATASET_PREFIX)}
    logger.info(
        f"DataSource {applied} → {latest}：变化数据集 "
        f"{sorted(p.removeprefix(DATASET_PREFIX) for p in dataset_changes) or '无'}"
    )
    return UpdatePlan(tag=latest, changed=dataset_changes)
