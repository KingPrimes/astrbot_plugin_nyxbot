"""CDN Data Source client / CDN 数据源客户端

封装从 CDN 获取 Warframe 配置数据（别名、节点等）的接口。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from astrbot.api import logger

from ..config import get_wf_data_source_cdn
from ..util import (
    fetch_json_with_retry,
    RetryLogLevel,
    get_public_data_path,
    download_file,
    decompress_lzma_auto,
)
from .api import WF_PUBLIC_EXPORT_INDEX, WF_PUBLIC_EXPORT_MANIFESTS


ExportDir: str = get_public_data_path() + "/export"
"""导出数据目录"""
ExportHash: str = ExportDir + "/Hash.json"
"""导出数据Hash列表"""
Key: str = "zh"
"""导出数据语言"""
ExportIndexPath: str | None = None
"""解压后的 ExportIndex 文件路径，由 _dc_export_lzma() 设置"""


async def _fetch_export_lzma_file() -> bool:
    """下载 CDN 上的 Warframe 公共导出索引文件（LZMA 压缩）。

    Returns:
        bool: 下载成功返回 True，失败返回 False。
    """
    url = WF_PUBLIC_EXPORT_INDEX % Key
    output = str(Path(ExportDir) / f"index_{Key}.txt.lzma")
    return await download_file(url=url, output=output)

async def _dc_export_lzma() -> bool:
    """下载并解压 Warframe 公共导出索引文件。

    先通过 _fetch_export_lzma_file() 下载 lzma 压缩包，下载成功后
    自动解压到 ExportDir，并将解压后的文件路径保存到全局变量
    ExportIndexPath 中，供其他函数使用。

    Returns:
        bool: 下载+解压全部成功返回 True，任一环节失败返回 False。
    """
    global ExportIndexPath

    if not await _fetch_export_lzma_file():
        return False

    lzma_path = str(Path(ExportDir) / f"index_{Key}.txt.lzma")
    result = decompress_lzma_auto(lzma_path, ExportDir)

    if result is not None:
        ExportIndexPath = str(result)
        return True

    return False

async def _compare_hash(lines: list[str]) -> dict[str, str]:
    """对比 LZMA 索引 Hash 值并保存快照，返回发生变化的条目。

    读取每一行（格式: ExportFile!HashValue），与本地 ExportHash
    JSON 文件中的旧值对比，写出新的 Hash 快照后返回 Hash
    值发生变化的条目。

    Args:
        lines: 解压后的索引文件内容，每行格式为 "filename!hash"

    Returns:
        dict[str, str]: 发生变化的条目 {filename: new_hash}
    """
    # 1. 解析当前 hash
    current: dict[str, str] = {}
    for line in lines:
        line = line.strip()
        if "!" in line:
            key, _, value = line.partition("!")
            current[key] = value

    # 2. 读取旧 hash 快照
    old: dict[str, str] = {}
    export_hash_path = Path(ExportHash)
    if export_hash_path.exists():
        try:
            old = json.loads(export_hash_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("ExportHash 文件损坏，将视为首次运行")

    # 3. 写出新 hash 快照
    export_hash_path.parent.mkdir(parents=True, exist_ok=True)
    export_hash_path.write_text(
        json.dumps(current, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 4. 返回发生变化的条目
    changed: dict[str, str] = {}
    for key, new_hash in current.items():
        old_hash = old.get(key)
        if old_hash != new_hash:
            changed[key] = new_hash

    return changed

async def _get_export_file(line: str) -> bool:
    """下载单个 Warframe 公共导出文件。

    Args:
        line: 索引行，格式为 "ExportWeapons_zh.json!hash_value"

    Returns:
        bool: 下载成功返回 True，失败返回 False。
    """
    url = WF_PUBLIC_EXPORT_MANIFESTS % line
    filename = line.split("!", 1)[0]
    output = str(Path(ExportDir) / filename)
    return await download_file(url=url, output=output)

async def sever_export_files() -> bool:
    """下载 Warframe 公共导出数据文件。

    完整流程：
    1. 下载并解压 LZMA 索引文件
    2. 对比 Hash 值，判断是否有更新
    3. 如有变更，逐一下载各个导出文件（跳过 ExportRecipes / ExportFusionBundles）

    Returns:
        bool: 全部操作成功返回 True，任一环节失败返回 False。
    """
    # 步骤1: 下载并解压 LZMA 索引
    if not await _dc_export_lzma():
        logger.error("下载或解压 LZMA 索引文件失败")
        return False

    # 步骤2: 读取解压后的索引文件
    if ExportIndexPath is None:
        logger.error("ExportIndexPath 未设置，_dc_export_lzma 可能未正确执行")
        return False

    index_path = Path(ExportIndexPath)
    if not index_path.exists():
        logger.error(f"索引文件不存在: {ExportIndexPath}")
        return False

    lines = index_path.read_text(encoding="utf-8").splitlines()

    # 步骤3: 对比 Hash
    compared = await _compare_hash(lines)
    if not compared:
        logger.info("LZMA 数据无变化，忽略此次更新")
        return True

    # 步骤4: 下载导出文件
    success = True
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 跳过不需要的导出文件
        if "ExportRecipes" in line or "ExportFusionBundles" in line:
            continue
        if not await _get_export_file(line):
            logger.error(f"下载导出文件失败: {line}")
            success = False

    return success


class DataSourceClient:
    """CDN 数据源客户端。

    用于从 CDN 获取 Warframe 辅助数据，如别名映射、星图节点等。
    """

    @classmethod
    def _base_url(cls) -> str:
        """获取当前配置的 CDN 基础 URL。"""
        return get_wf_data_source_cdn()

    @classmethod
    async def fetch_alias(cls) -> Optional[list[dict]]:
        """获取别名数据"""
        url = f"{cls._base_url()}/warframe/alias.json"
        return await fetch_json_with_retry(
            url,
            log_templates={
                RetryLogLevel.WARNING: "获取别名数据失败（第 {attempt}/{max_retries} 次），{retry_delay} 秒后重试...",
                RetryLogLevel.ERROR: "获取别名数据失败，已重试 {max_retries} 次，放弃",
            },
        )

    @classmethod
    async def fetch_nodes(cls) -> Optional[list[dict]]:
        """获取星图节点数据"""
        url = f"{cls._base_url()}/warframe/nodes.json"
        return await fetch_json_with_retry(
            url,
            log_templates={
                RetryLogLevel.WARNING: "获取星图节点数据失败（第 {attempt}/{max_retries} 次），{retry_delay} 秒后重试...",
                RetryLogLevel.ERROR: "获取星图节点数据失败，已重试 {max_retries} 次，放弃",
            },
        )

    @classmethod
    async def fetch_state_translations(cls) -> Optional[list[dict]]:
        """获取翻译数据"""
        url = f"{cls._base_url()}/warframe/state_translation.json"
        return await fetch_json_with_retry(
            url,
            log_templates={
                RetryLogLevel.WARNING: "获取翻译数据失败（第 {attempt}/{max_retries} 次），{retry_delay} 秒后重试...",
                RetryLogLevel.ERROR: "获取翻译数据失败，已重试 {max_retries} 次，放弃",
            },
        )

    @classmethod
    async def fetch_rive_tion(cls) -> Optional[list[dict]]:
        """获取Riven Tion 紫卡属性查询参数"""
        url = f"{cls._base_url()}/warframe/market_riven_tion.json"
        return await fetch_json_with_retry(
            url,
            log_templates={
                RetryLogLevel.WARNING: "获取紫卡属性查询参数失败（第 {attempt}/{max_retries} 次），{retry_delay} 秒后重试...",
                RetryLogLevel.ERROR: "获取紫卡属性查询参数失败，已重试 {max_retries} 次，放弃",
            },
        )

    @classmethod
    async def fetch_riven_tion_alias(cls) -> Optional[list[dict]]:
        """获取Riven Tion Alias 紫卡属性查询别名"""
        url = f"{cls._base_url()}/warframe/market_riven_tion_alias.json"
        return await fetch_json_with_retry(
            url,
            log_templates={
                RetryLogLevel.WARNING: "获取紫卡属性查询别名失败（第 {attempt}/{max_retries} 次），{retry_delay} 秒后重试...",
                RetryLogLevel.ERROR: "获取紫卡属性查询别名失败，已重试 {max_retries} 次，放弃",
            },
        )

    @classmethod
    async def fetch_reward_pool(cls) -> Optional[list[dict]]:
        """获取 奖励池 数据"""
        url = f"{cls._base_url()}/warframe/reward_pool.json"
        return await fetch_json_with_retry(
            url,
            log_templates={
                RetryLogLevel.WARNING: "获取奖励池数据失败（第 {attempt}/{max_retries} 次），{retry_delay} 秒后重试...",
                RetryLogLevel.ERROR: "获取奖励池数据失败，已重试 {max_retries} 次，放弃",
            },
        )

    @classmethod
    async def fetch_riven_analyse_trend(cls) -> Optional[list[dict]]:
        """获取 紫卡计算器 数据"""
        url = f"{cls._base_url()}/warframe/riven_analyse_trend.json"
        return await fetch_json_with_retry(
            url,
            log_templates={
                RetryLogLevel.WARNING: "获取紫卡计算器数据失败（第 {attempt}/{max_retries} 次），{retry_delay} 秒后重试...",
                RetryLogLevel.ERROR: "获取紫卡计算器数据失败，已重试 {max_retries} 次，放弃",
            },
        ) 