"""Compress utilities / LZMA 解压工具

基于 Python 标准库 lzma 模块的解压入口
支持 LZMA-Alone (.lzma) 和 XZ (.xz) 格式的流式解压。

使用方式:
    from src.util import decompress_lzma, decompress_lzma_auto

    # 指定完整输出路径
    decompress_lzma("data/index_zh.txt.lzma", "output/index_zh.txt")

    # 自动去除后缀，解压到指定目录
    output = decompress_lzma_auto("data/index_zh.txt.lzma", "output/")
    # output = Path("output/index_zh.txt")
"""

from __future__ import annotations

import lzma
from pathlib import Path
from typing import Optional

from astrbot.api import logger

# 默认分块大小：1MB
_DEFAULT_CHUNK_SIZE = 1024 * 1024

# 已知压缩后缀及其对应的去除规则
_KNOWN_SUFFIXES: dict[str, int] = {
    ".lzma": 5,
    ".xz": 3,
}


def decompress_lzma(
    source: str | Path,
    output: str | Path,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
) -> bool:
    """解压 LZMA-Alone / XZ 压缩文件到指定的完整输出路径。

    采用流式分块读写，避免大文件撑爆内存。底层使用 Python 标准库

    Args:
        source: 源压缩文件路径（.lzma / .xz）。
        output: 解压后的目标文件完整路径。
        chunk_size: 分块大小（字节），默认 1MB。

    Returns:
        bool: 解压成功返回 True，失败返回 False。
    """
    source_path = Path(source)
    output_path = Path(output)

    if not source_path.exists():
        logger.error(f"解压失败: 源文件不存在 - {source_path}")
        return False

    if not source_path.is_file():
        logger.error(f"解压失败: 源路径不是文件 - {source_path}")
        return False

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with lzma.open(source_path, "rb") as f_in:
            with open(output_path, "wb") as f_out:
                while True:
                    chunk = f_in.read(chunk_size)
                    if not chunk:
                        break
                    f_out.write(chunk)

        logger.info(f"LZMA 解压成功: {source_path.name} → {output_path}")
        return True

    except lzma.LZMAError as e:
        logger.error(f"LZMA 解压失败: 无效的压缩数据 - {source_path} - {e}")
        return False
    except OSError as e:
        logger.error(f"LZMA 解压失败: 磁盘 I/O 错误 - {output_path} - {e}")
        return False
    except Exception as e:
        logger.error(f"LZMA 解压失败: 未知错误 - {source_path} - {e}")
        return False


def decompress_lzma_auto(
    source: str | Path,
    output_dir: str | Path,
) -> Optional[Path]:
    """自动去除压缩后缀，解压到指定目录。

    后缀处理规则:
        - 以 .lzma 结尾 → 去掉 .lzma
        - 以 .xz 结尾 → 去掉 .xz
        - 无已知后缀 → 追加 .decompressed

    Args:
        source: 源压缩文件路径。
        output_dir: 解压输出目录。

    Returns:
        Optional[Path]: 解压成功返回输出文件路径，失败返回 None。

    Example:
        >>> decompress_lzma_auto("data/index_zh.txt.lzma", "output/")
        Path("output/index_zh.txt")
        >>> decompress_lzma_auto("data/archive.xz", "output/")
        Path("output/archive")
    """
    source_path = Path(source)
    output_dir_path = Path(output_dir)

    # 确定输出文件名
    stem = source_path.name
    output_name: str | None = None
    for suffix, cut in _KNOWN_SUFFIXES.items():
        if stem.endswith(suffix):
            output_name = stem[:-cut]
            break

    if output_name is None:
        output_name = f"{stem}.decompressed"
        logger.warning(
            f"源文件无已知压缩后缀，将使用 '{output_name}' 作为输出文件名"
        )

    output_path = output_dir_path / output_name

    success = decompress_lzma(source_path, output_path)
    return output_path if success else None