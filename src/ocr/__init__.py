"""OCR package / OCR 识别包

推理在独立子进程中执行（见 ``worker.py``），主进程只做代理：
原生层崩溃不会波及 bot 主进程。
"""
from __future__ import annotations

from .cpu_caps import CpuCaps, detect
from .ocr_service import OcrService, OcrUnavailableError

__all__ = [
    "CpuCaps",
    "OcrService",
    "OcrUnavailableError",
    "detect",
]
