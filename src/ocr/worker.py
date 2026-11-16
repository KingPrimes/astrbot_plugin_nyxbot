"""OCR 子进程 worker：在独立解释器里跑 RapidOCR，任何原生崩溃都不波及主进程。

为什么要有这个进程
------------------
``paddlepaddle`` 3.x 的 wheel 是编译期硬编码 AVX 的，在只有 SSE4.2 的
CPU（如 Pentium G2030）上 ``import paddle`` 会直接触发 SIGILL。SIGILL 是
原生信号，Python 层没有任何办法捕获——``try/except``、``gather(
return_exceptions=True)`` 全部无效，整个 AstrBot 进程当场消失。

换成 onnxruntime 后这条具体路径没了（它有运行时 CPUID 分派），但**任何**
原生推理库都可能在特定硬件上踩同类问题。把 OCR 关进子进程后，最坏情况
是 worker 死掉，主进程感知到 ``returncode`` 并降级为「OCR 不可用」。

协议
----
stdin/stdout 上的二进制帧，避免与日志争抢：

    +----------------+---------------------------+
    | 4 字节大端长度 | pickle 序列化的 dict 载荷 |
    +----------------+---------------------------+

请求：``{"cmd": "recognize", "img_png": bytes}`` / ``{"cmd": "ping"}``
      / ``{"cmd": "shutdown"}``
响应：``{"ok": True, "items": [...]}`` 或 ``{"ok": False, "error": "..."}``

stdout 在 import rapidocr **之前**就被重定向到 stderr，协议走 dup 出来的
原始 fd——这样 rapidocr / onnxruntime 内部任何 ``print`` 都不会污染协议流。

图片按 PNG 字节传输而非 ndarray，原因有两个：一是压缩后体积小得多
（720×1080 紫卡截图约 300KB vs 原始 2.3MB），二是 rapidocr 对 ndarray
输入**不做通道转换**（默认当 BGR），而 bytes/PIL 输入会正确 RGB→BGR。

独立运行：``python worker.py``（自包含，不 import 包内其它模块）。
"""
from __future__ import annotations

import os
import pickle
import struct
import sys
import traceback
from typing import Any

# --------------------------------------------------------------------------
# stdout 保护：必须早于任何第三方 import
# --------------------------------------------------------------------------
# 复制一份原始 stdout 的 fd 专供协议使用，再把 fd 1 指向 stderr。
# 之后无论谁 print / 写 sys.stdout，都只会落到 stderr 日志里。
_PROTO_FD = os.dup(sys.stdout.fileno())
os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
_PROTO = os.fdopen(_PROTO_FD, "wb", buffering=0)
sys.stdout = sys.stderr  # Python 层也改道，避免缓冲差异

_FRAME_HEADER = struct.Struct("!I")
_MAX_FRAME = 64 * 1024 * 1024  # 64MB 上限，防御性上限，正常请求远小于此


def _write_frame(obj: Any) -> None:
    """把对象序列化成一帧写到协议流。"""
    payload = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
    _PROTO.write(_FRAME_HEADER.pack(len(payload)))
    _PROTO.write(payload)


def _read_exact(stream: Any, size: int) -> bytes | None:
    """从流里精确读 size 字节；父进程关闭管道时返回 None。"""
    chunks = []
    remaining = size
    while remaining > 0:
        chunk = stream.read(remaining)
        if not chunk:
            return None
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _read_frame() -> dict[str, Any] | None:
    """读一帧；管道结束或数据异常时返回 None。"""
    header = _read_exact(sys.stdin.buffer, _FRAME_HEADER.size)
    if header is None:
        return None
    (length,) = _FRAME_HEADER.unpack(header)
    if length <= 0 or length > _MAX_FRAME:
        return None
    body = _read_exact(sys.stdin.buffer, length)
    if body is None:
        return None
    try:
        msg = pickle.loads(body)
    except Exception:
        return None
    return msg if isinstance(msg, dict) else None


def _build_engine() -> Any:
    """构造 RapidOCR 引擎（onnxruntime / PP-OCRv6 small，模型随 wheel 内置）。"""
    from rapidocr import RapidOCR

    # log_level 调到 warning：worker 的日志会混在主进程日志里，
    # 每次识别的 INFO 行（用了哪个模型）属于噪音。
    return RapidOCR(params={"Global.log_level": "warning"})


def _warmup(engine: Any) -> None:
    """用一张带文字的小图预热。

    目的不是测性能，而是把「模型文件缺失 / 指令集不兼容 / onnxruntime
    加载失败」这类问题在启动阶段就暴露出来，而不是等第一条紫卡指令。

    必须画上真文字：纯白图会让检测阶段返回空结果并打一条 WARNING，
    那条告警会混进主进程日志，看着像故障。
    """
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (200, 64), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size=32)
    except TypeError:  # Pillow < 9.1 不支持 size 参数
        font = ImageFont.load_default()
    draw.text((10, 14), "OCR 123", fill=(0, 0, 0), font=font)
    engine(img)


def _recognize(engine: Any, png_bytes: bytes) -> list[dict[str, Any]]:
    """识别一张图，返回 ``[{text, confidence, box}]``。"""
    result = engine(png_bytes)
    if result is None or result.txts is None:
        return []

    boxes = result.boxes
    scores = result.scores
    items: list[dict[str, Any]] = []
    for idx, text in enumerate(result.txts):
        score = float(scores[idx]) if idx < len(scores) else 0.0
        box = None
        if boxes is not None and idx < len(boxes):
            box = boxes[idx].tolist() if hasattr(boxes[idx], "tolist") else boxes[idx]
        items.append({"text": text, "confidence": score, "box": box})
    return items


def main() -> int:
    # 先建引擎再报 ready：让主进程明确知道这个 worker 能不能干活。
    # 失败就直接退出，主进程看到 returncode 后降级，不会留下僵尸进程。
    try:
        engine = _build_engine()
        _warmup(engine)
    except BaseException as exc:  # noqa: BLE001 - 任何失败都要回报而非静默
        _write_frame({
            "ok": False,
            "event": "ready",
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
        })
        return 1

    _write_frame({
        "ok": True,
        "event": "ready",
        "pid": os.getpid(),
        "python": sys.version.split()[0],
    })

    while True:
        msg = _read_frame()
        if msg is None:
            # 父进程关闭了管道（正常退出或被杀），直接结束
            return 0

        cmd = msg.get("cmd")
        if cmd == "shutdown":
            return 0
        if cmd == "ping":
            _write_frame({"ok": True, "pong": True})
            continue
        if cmd != "recognize":
            _write_frame({"ok": False, "error": f"未知命令: {cmd!r}"})
            continue

        try:
            items = _recognize(engine, msg["img_png"])
        except BaseException as exc:  # noqa: BLE001
            # 识别阶段的异常不让 worker 退出：单张图失败不该毁掉整个引擎
            _write_frame({
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(),
            })
            continue

        _write_frame({"ok": True, "items": items})


if __name__ == "__main__":
    sys.exit(main())
