"""CPU 指令集探测。

用途：在加载任何原生推理库**之前**判断这台机器能跑什么。

背景（2026-11-17 线上事故）：``paddlepaddle`` 3.x 的 Linux wheel 是编译期
硬编码 AVX 的，在只有 SSE4.2 的 CPU（Pentium G2030 / Ivy Bridge）上
``import paddle`` 就会执行到 AVX 指令，触发 SIGILL——这是原生信号，
Python 的 ``try/except`` 和 ``asyncio.gather(return_exceptions=True)``
都拦不住，整个 AstrBot 进程直接消失。所以能力判断必须发生在 import 之前，
而不是指望异常处理兜底。

Linux 读 ``/proc/cpuinfo`` 最可靠；Windows / macOS 拿不到 x86 flags，
返回 ``None`` 表示「未知」——未知不等于缺失，调用方不应据此阻止加载。
"""
from __future__ import annotations

import functools
import platform
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# /proc/cpuinfo 里 x86 用 flags、ARM 用 Features；大小写不统一，统一转小写比对
_FLAG_KEYS = ("flags", "Features")


@dataclass(frozen=True)
class CpuCaps:
    """一次探测的结果快照。

    ``None`` 表示该平台拿不到指令集信息（Windows / macOS），
    与「确认不支持」是两回事，不要混用。
    """

    model: str
    flags: frozenset[str]
    has_sse42: bool | None
    has_avx: bool | None
    has_avx2: bool | None

    @property
    def known(self) -> bool:
        """是否真的读到了指令集列表。"""
        return bool(self.flags)

    def describe(self) -> str:
        """一行可读描述，用于启动日志。"""
        if not self.known:
            return f"{self.model}（{platform.system()} 无法读取指令集，按未知处理）"
        marks = []
        for name, value in (
            ("SSE4.2", self.has_sse42),
            ("AVX", self.has_avx),
            ("AVX2", self.has_avx2),
        ):
            # 三态：None 是「未知」，不能与明确的「不支持」(False) 混为一谈
            mark = "?" if value is None else ("Y" if value else "N")
            marks.append(f"{name}={mark}")
        return f"{self.model}（{' '.join(marks)}）"

    @property
    def avx_missing(self) -> bool:
        """确认缺失 AVX。仅当探测成功且没有 avx 标志时为真。"""
        return self.has_avx is False


def _read_proc_cpuinfo(path: Path = Path("/proc/cpuinfo")) -> tuple[str, frozenset[str]]:
    """解析 /proc/cpuinfo，返回 (型号, 指令集集合)。

    只取第一个处理器块：同构机器上各核 flags 相同，异构大小核也以
    首个逻辑核为准（够用，且避免把不同核的 flags 混成一个并集）。
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "", frozenset()

    model = ""
    flags: frozenset[str] = frozenset()
    for line in text.splitlines():
        if not line.strip():
            # 空行代表一个处理器块结束；已经拿到所需信息就不再往下读
            if model and flags:
                break
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if key == "model name" and not model:
            model = value
        elif key in _FLAG_KEYS and not flags:
            flags = frozenset(value.lower().split())
    return model, flags


def _macos_flags() -> frozenset[str]:
    """macOS 用 sysctl 拿 CPU 特性；失败返回空集。"""
    import subprocess

    try:
        out = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.features", "machdep.cpu.leaf7_features"],
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return frozenset()
    raw = out.stdout.decode("utf-8", "replace").lower()
    return frozenset(re.split(r"[\s:]+", raw))


def _windows_model() -> str:
    """Windows 从注册表拿 CPU 商品名（platform.processor() 只给 "AMD64 Family..."）。"""
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
        ) as key:
            value = winreg.QueryValueEx(key, "ProcessorNameString")[0]
            return str(value).strip()
    except (OSError, ImportError, IndexError):
        return platform.processor() or platform.machine()


@functools.lru_cache(maxsize=1)
def detect() -> CpuCaps:
    """探测当前 CPU 能力（结果缓存，进程内只读一次）。"""
    if sys.platform.startswith("linux"):
        model, flags = _read_proc_cpuinfo()
    elif sys.platform == "darwin":
        model, flags = platform.processor() or "Apple Silicon", _macos_flags()
    else:
        # Windows 拿不到 x86 flags，型号走注册表
        model, flags = _windows_model(), frozenset()

    if not flags:
        return CpuCaps(model=model, flags=flags, has_sse42=None, has_avx=None, has_avx2=None)

    return CpuCaps(
        model=model,
        flags=flags,
        has_sse42="sse4_2" in flags,
        has_avx="avx" in flags,
        has_avx2="avx2" in flags,
    )


def reset_cache() -> None:
    """清空探测缓存（测试用）。"""
    detect.cache_clear()
