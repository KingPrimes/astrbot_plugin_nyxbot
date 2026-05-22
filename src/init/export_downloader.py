"""Warframe Public Export Data Downloader / Warframe 公共导出数据下载器

提供从 CDN 下载、解压、校验 Warframe 公共导出数据文件的工具函数。
原位于 src/api/data_source.py，现迁移至此。

Functions:
    sever_export_files() — 主入口：下载并同步最新的导出数据
"""
from __future__ import annotations

import json
from pathlib import Path

from astrbot.api import logger

from ..api.api import WF_PUBLIC_EXPORT_INDEX, WF_PUBLIC_EXPORT_MANIFESTS
from ..util import (
    decompress_lzma_auto,
    download_file,
    get_public_data_path,
)

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


# ══════════════════════════════════════════════════════════════════════
# Hash.json 内存缓存（避免重复 IO：从 ~15 次降为 1 次）
# ══════════════════════════════════════════════════════════════════════
_hash_cache: dict[str, str] = {}
_hash_cache_mtime: float = 0.0


async def _load_hash_data() -> dict[str, str]:
    """加载 Hash.json 到内存缓存（基于文件 mtime 的惰性失效）。

    Returns:
        Hash.json 解析后的 dict，文件不存在或解析失败时返回 {}。
    """
    global _hash_cache, _hash_cache_mtime
    hash_path = Path(ExportHash)
    mtime = hash_path.stat().st_mtime if hash_path.exists() else 0.0
    if mtime == _hash_cache_mtime:
        return _hash_cache
    try:
        _hash_cache = json.loads(hash_path.read_text(encoding="utf-8"))
        _hash_cache_mtime = mtime
    except (json.JSONDecodeError, OSError):
        _hash_cache = {}
        _hash_cache_mtime = 0.0
    return _hash_cache


async def resolve_export_filename(prefix: str) -> str | None:
    """从 Hash.json 中查找匹配指定前缀的导出文件名，避免硬编码语言后缀。

    例如:
        resolve_export_filename("ExportRegions") → "ExportRegions_zh.json"
        resolve_export_filename("ExportWeapons") → "ExportWeapons_zh.json"

    Hash.json 的 key 是完整的导出文件名（含语言后缀），
    因此只需遍历 key 并匹配前缀即可支持任意语言。

    通过 _load_hash_data() 使用内存缓存，避免每次调用都重新读取文件。

    Args:
        prefix: 文件前缀，如 "ExportRegions", "ExportWeapons", "ExportSortieRewards"

    Returns:
        str | None: 实际文件名（含扩展名），未找到时返回 None
    """
    hash_data = await _load_hash_data()
    if not hash_data:
        logger.warning(f"Hash.json 为空或不存在，无法解析导出文件名: {prefix}")
        return None

    for filename in hash_data:
        if isinstance(filename, str) and filename.startswith(prefix):
            return filename

    logger.warning(f"Hash.json 中未找到以 '{prefix}' 开头的文件")
    return None
