"""OCR Service / RapidOCR 子进程代理

引擎与模型
----------
推理走 **RapidOCR 3.x + onnxruntime**，模型是 wheel 内置的 PP-OCRv6 small
（det 9.9MB / rec 21MB / cls 0.6MB），首次使用不需要联网下载。这套组合与
NyxBot-Go 的 ``internal/ocr`` 同源（PP-OCRv6 + onnxruntime 1.23.1），
两边识别行为一致。

为什么换掉 PaddleOCR
--------------------
``paddlepaddle`` 3.x 的 Linux wheel 是**编译期硬编码 AVX** 的，在只有
SSE4.2 的 CPU（Pentium G2030 / Ivy Bridge）上 ``import paddle`` 就会执行到
AVX 指令并触发 SIGILL。这是原生信号，Python 层完全拦不住——2026-11-17
线上事故里 AstrBot 进程就是这样被打死的，日志停在「装完 paddle 19 秒后」。
onnxruntime 的 CPU 内核按 CPUID 运行时选择（SSE/AVX/AVX2 多套实现），
所以同一份代码在有 AVX 和无 AVX 的机器上都能跑。

为什么还要子进程
----------------
指令集只是原生库风险的一种。把 OCR 关进独立解释器后，任何原生层崩溃
（SIGILL / SIGSEGV / OOM killer）都只影响 worker，主进程能通过
``returncode`` 感知并降级成「OCR 不可用」，而不是整个 bot 消失。

对外契约
--------
``recognize`` 返回 ``[{text, confidence, box}]``，
``recognize_text_only`` 返回 ``list[str]``（置信度 > 0.5），与旧实现一致。
"""
from __future__ import annotations

import asyncio
import contextlib
import io
import pickle
import struct
import sys
import time
from pathlib import Path
from typing import Any

from PIL import Image

from astrbot.api import logger

from . import cpu_caps

# worker 脚本与本文件同目录；用绝对路径，避免受 cwd 影响
_WORKER_PATH = Path(__file__).with_name("worker.py")

_FRAME_HEADER = struct.Struct("!I")
_MAX_FRAME = 64 * 1024 * 1024

# 超时：目标机器是 2013 年的双核 Pentium，给足余量
_READY_TIMEOUT = 180.0  # 模型加载 + 预热
_RECOGNIZE_TIMEOUT = 120.0  # 单张图识别
_SHUTDOWN_TIMEOUT = 5.0

# 崩溃重启：窗口内最多重启 _MAX_RESTARTS 次，避免崩溃循环刷日志
_MAX_RESTARTS = 3
_RESTART_WINDOW = 300.0

# 低于该置信度的识别结果直接丢弃（与旧实现的 0.5 保持一致）
_MIN_CONFIDENCE = 0.5


class OcrUnavailableError(RuntimeError):
    """OCR 引擎不可用（未初始化、子进程崩溃、识别失败）。"""


class OcrService:
    """RapidOCR 子进程代理（单例）。

    由 ``main.py`` 在插件启动时显式初始化；未初始化时调用 ``recognize``
    会尝试惰性拉起 worker，仍失败则抛 :class:`OcrUnavailableError`。
    """

    _instance: OcrService | None = None

    def __new__(cls) -> OcrService:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_inited", False):
            return
        self._inited = True
        self._proc: asyncio.subprocess.Process | None = None
        self._ready = False
        self._req_lock: asyncio.Lock | None = None
        self._start_lock: asyncio.Lock | None = None
        self._restarts = 0
        self._last_failure_at = 0.0
        self._last_error = ""

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    async def initialize(self) -> None:
        """拉起 OCR 子进程。

        失败只记日志不抛异常——OCR 是可选能力，不该连累插件初始化。
        调用方（``riven_analyse``）会在真正需要识别时拿到明确的错误。

        必须整体加锁：``initialize`` 和 ``_ensure_ready`` 可能被不同协程
        同时触发，两边都会在 ``_start`` 开头的 ``close()`` 看到 ``_proc is None``，
        于是各自拉起一个 worker，最终只有一个被 ``_proc`` 引用，另一个
        无人回收。锁在这里的成本为零，能省掉一整类难查的进程泄漏。

        注：Windows 上 venv 的 ``python.exe`` 是 launcher，一个 worker 在
        进程列表里会显示成两层（launcher + 真实解释器），这是正常现象，
        不要当成重复拉起。
        """
        async with self._start_lock_obj():
            if self.available:
                return

            caps = cpu_caps.detect()
            logger.info(f"OCR 宿主 CPU: {caps.describe()}")
            if caps.avx_missing:
                logger.warning(
                    "该 CPU 不支持 AVX，onnxruntime 将回退到 SSE 路径，OCR 推理会明显变慢"
                    "（功能不受影响）"
                )

            try:
                await self._start()
            except Exception as e:  # noqa: BLE001 - 初始化失败不应中断插件启动
                logger.error(f"OCR 子进程启动失败，OCR 功能不可用: {e}")

    async def close(self) -> None:
        """关闭 worker（插件重载 / 进程退出时调用）。

        ``CancelledError`` 经清理后向外透传，绝不吞掉——否则调用方
        （``terminate()``）的任务取消会失效（CLAUDE.md 约定）。
        """
        proc = self._proc
        self._proc = None
        self._ready = False
        if proc is None:
            return

        try:
            if proc.returncode is None and proc.stdin is not None:
                with contextlib.suppress(Exception):
                    await self._send(proc, {"cmd": "shutdown"})
                try:
                    await asyncio.wait_for(proc.wait(), _SHUTDOWN_TIMEOUT)
                except asyncio.TimeoutError:
                    self._kill_worker(proc)

            # 统一回收一次：已退出的进程立即返回，避免僵尸堆积；
            # 加超时保护，避免极端情况下 kill 仍不退出时无限挂住 terminate()
            with contextlib.suppress(Exception):
                await asyncio.wait_for(proc.wait(), _SHUTDOWN_TIMEOUT)
        except asyncio.CancelledError:
            # 取消时仍尽力回收 worker，再把取消信号继续向上传播
            self._kill_worker(proc)
            raise

    @staticmethod
    def _kill_worker(proc: asyncio.subprocess.Process) -> None:
        """同步强杀 worker 并关闭 stdin（取消 / 超时路径的尽力清理）。"""
        # Windows 上 venv 的 python.exe 是 launcher，kill 只终结它；
        # 关 stdin 让 worker 读到 EOF 后自行退出，避免留下孤儿进程
        with contextlib.suppress(Exception):
            proc.kill()
        if proc.stdin is not None:
            with contextlib.suppress(Exception):
                proc.stdin.close()

    @property
    def available(self) -> bool:
        """当前是否有可用的 OCR 引擎。"""
        return self._ready and self._alive()

    @property
    def last_error(self) -> str:
        """最近一次失败原因，供指令层展示。"""
        return self._last_error

    # ------------------------------------------------------------------
    # 识别
    # ------------------------------------------------------------------
    async def recognize(self, image: Image.Image | str) -> list[dict[str, Any]]:
        """识别图片中的文字。

        Args:
            image: PIL Image 对象或图片路径。

        Returns:
            识别结果列表，每个元素包含 ``text`` / ``confidence`` / ``box``，
            ``box`` 为四点多边形 ``[[x1,y1],...]``。

        Raises:
            OcrUnavailableError: 引擎不可用或识别失败。
        """
        await self._ensure_ready()

        # PNG 编码是 CPU 活，丢到线程里；顺带把图片体积从 MB 级压到几百 KB
        payload = await asyncio.to_thread(self._encode_image, image)

        proc = self._proc
        if proc is None:
            raise OcrUnavailableError("OCR 子进程未运行")
        lock = self._request_lock()

        async with lock:
            # 等锁期间 worker 可能已经挂了，进来后再确认一次
            if proc.returncode is not None:
                self._mark_failed(f"OCR 子进程已退出（returncode={proc.returncode}）")
                raise OcrUnavailableError(self._last_error)

            await self._send(proc, {"cmd": "recognize", "img_png": payload})
            frame = await self._read_frame(proc, _RECOGNIZE_TIMEOUT)

        if frame is None:
            self._mark_failed("OCR 子进程无响应或已崩溃")
            raise OcrUnavailableError(self._last_error)
        if not frame.get("ok"):
            raise OcrUnavailableError(str(frame.get("error") or "OCR 识别失败"))
        return list(frame.get("items") or [])

    async def recognize_text_only(self, image: Image.Image | str) -> list[str]:
        """仅返回识别到的文字列表（过滤低置信度结果）。"""
        results = await self.recognize(image)
        return [r["text"] for r in results if r["confidence"] > _MIN_CONFIDENCE]

    # ------------------------------------------------------------------
    # 内部：启动与健康检查
    # ------------------------------------------------------------------
    def _alive(self) -> bool:
        proc = self._proc
        return proc is not None and proc.returncode is None

    def _request_lock(self) -> asyncio.Lock:
        if self._req_lock is None:
            self._req_lock = asyncio.Lock()
        return self._req_lock

    def _start_lock_obj(self) -> asyncio.Lock:
        if self._start_lock is None:
            self._start_lock = asyncio.Lock()
        return self._start_lock

    async def _ensure_ready(self) -> None:
        """确保 worker 可用；必要时尝试重启（带频率限制）。"""
        if self.available:
            return

        async with self._start_lock_obj():
            # 双检：等锁期间可能已被别的协程拉起
            if self.available:
                return

            if self._restarts >= _MAX_RESTARTS:
                # 窗口外允许再试，避免偶发失败导致永久禁用
                if time.monotonic() - self._last_failure_at < _RESTART_WINDOW:
                    raise OcrUnavailableError(
                        f"OCR 引擎不可用（已连续重启 {self._restarts} 次）：{self._last_error}"
                    )
                self._restarts = 0

            self._restarts += 1
            try:
                await self._start()
            except Exception as e:  # noqa: BLE001
                self._mark_failed(f"OCR 子进程启动失败: {e}")
                raise OcrUnavailableError(self._last_error) from e

            if not self.available:
                raise OcrUnavailableError(self._last_error or "OCR 引擎未就绪")

    async def _start(self) -> None:
        """启动 worker 并等待 ready 帧。"""
        await self.close()

        if not _WORKER_PATH.exists():
            raise OcrUnavailableError(f"OCR worker 脚本缺失: {_WORKER_PATH}")

        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                str(_WORKER_PATH),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                # stderr 继承父进程：rapidocr 的告警直接进框架日志，便于排障
                stderr=None,
            )
        except NotImplementedError as e:
            # 某些事件循环实现（如 Windows 的 SelectorEventLoop）不支持子进程
            raise OcrUnavailableError(
                "当前事件循环不支持子进程，OCR 无法以隔离模式运行"
            ) from e

        self._proc = proc
        frame = await self._read_frame(proc, _READY_TIMEOUT)
        if frame is None:
            await self.close()
            raise OcrUnavailableError("OCR 子进程启动超时或提前退出")

        if not frame.get("ok"):
            detail = frame.get("error") or "未知错误"
            tb = frame.get("traceback")
            if tb:
                logger.debug(f"OCR worker 启动失败详情:\n{tb}")
            await self.close()
            raise OcrUnavailableError(f"OCR 引擎初始化失败: {detail}")

        self._ready = True
        self._last_error = ""
        logger.info(
            "OCR 引擎就绪（RapidOCR / onnxruntime / PP-OCRv6，worker pid=%s）",
            frame.get("pid", "?"),
        )

    def _mark_failed(self, reason: str) -> None:
        self._ready = False
        self._last_error = reason
        self._last_failure_at = time.monotonic()
        logger.error(reason)

    # ------------------------------------------------------------------
    # 内部：帧协议
    # ------------------------------------------------------------------
    @staticmethod
    async def _send(proc: asyncio.subprocess.Process, obj: dict[str, Any]) -> None:
        if proc.stdin is None:
            raise OcrUnavailableError("OCR 子进程 stdin 不可用")
        payload = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
        proc.stdin.write(_FRAME_HEADER.pack(len(payload)) + payload)
        await proc.stdin.drain()

    @staticmethod
    async def _read_frame(
        proc: asyncio.subprocess.Process, timeout: float
    ) -> dict[str, Any] | None:
        """读一帧；超时、EOF、解码失败统一返回 None。"""
        if proc.stdout is None:
            return None
        try:
            header = await asyncio.wait_for(
                proc.stdout.readexactly(_FRAME_HEADER.size), timeout
            )
            (length,) = _FRAME_HEADER.unpack(header)
            if length <= 0 or length > _MAX_FRAME:
                return None
            body = await asyncio.wait_for(proc.stdout.readexactly(length), timeout)
        except (asyncio.TimeoutError, asyncio.IncompleteReadError, ConnectionError):
            return None
        except asyncio.CancelledError:
            raise
        except Exception:
            return None

        try:
            frame = pickle.loads(body)
        except Exception:
            return None
        return frame if isinstance(frame, dict) else None

    # ------------------------------------------------------------------
    # 内部：图片编码
    # ------------------------------------------------------------------
    @staticmethod
    def _encode_image(image: Image.Image | str) -> bytes:
        """把输入统一成 PNG/原始图片字节。

        传字节而不是 ndarray 是有原因的：rapidocr 对 ndarray 输入**不做通道
        转换**（默认当 BGR），而 bytes/PIL 输入会走 RGB→BGR。跨进程传字节
        既避开这个坑，体积也只有原始像素的 1/8 左右。
        """
        if isinstance(image, Image.Image):
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            return buf.getvalue()
        return Path(image).read_bytes()
