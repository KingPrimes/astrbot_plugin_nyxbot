"""OCR Service / PaddleOCR 文字识别服务

已适配 paddleocr 3.x API（PP-OCRv5 系列）。相对 2.x 的差异：

* 移除 ``use_angle_cls`` / ``show_log`` / ``use_gpu`` / ``det_model_dir`` 等旧参数；
  改用 ``use_doc_orientation_classify`` / ``use_doc_unwarping``
  / ``use_textline_orientation`` / ``device``。
* 推理入口改为 ``PaddleOCR.predict(img)``，返回的每个 ``OCRResult`` 把识别结果拆到
  ``rec_texts`` / ``rec_scores`` / ``rec_polys`` 三个数组中。
* paddle 3.x 的 PIR + oneDNN 后端在 Windows 上存在 PIR 属性转换错误
  ``ConvertPirAttribute2RuntimeAttribute not support``。修复方式：
  ``enable_mkldnn=False`` + ``engine_config`` 中 ``enable_new_ir: False``
  彻底绕过 PIR → oneDNN 路径。
* 默认使用 PP-OCRv5 **移动端**模型 (mobile_det / mobile_rec)，CPU 推理
  速度快于服务端模型 (server_det / server_rec)，紫卡截图精度足够。
* 模型自动下载至 paddle 默认缓存目录 ``~/.paddlex/official_models/``。

调用方契约 (``recognize`` 返回 ``[{text, confidence, box}]``,
``recognize_text_only`` 返回 ``list[str]``) 不变。
"""
from __future__ import annotations

import asyncio
import os
from typing import Any

import numpy as np
from PIL import Image

from astrbot.api import logger

# paddle 3.x 环境变量安全网（与构造参数互补确保 oneDNN 完全禁用）
os.environ["FLAGS_USE_ONEDNN"] = "0"
os.environ["FLAGS_USE_MKLDNN"] = "0"
os.environ.setdefault("KMP_AFFINITY", "disabled")
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")


async def _system_has_gpu() -> bool:
    """检测系统是否存在 NVIDIA GPU（不依赖 paddle）。"""
    try:
        proc = await asyncio.create_subprocess_exec(
            "nvidia-smi", "--query-gpu=name", "--format=csv,noheader",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        return proc.returncode == 0 and bool(stdout.decode().strip())
    except Exception:
        return False


class OcrService:
    """PaddleOCR 文字识别服务（优先 GPU，回退 CPU）。

    单例模式，由 main.py 在插件启动时显式初始化。
    """

    _instance: OcrService | None = None
    _ocr: Any = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self) -> None:
        """延迟初始化 OCR 引擎（paddleocr 3.x）。"""
        if self._initialized:
            return

        try:
            import paddle
            from paddleocr import PaddleOCR

            # GPU 检测
            # paddlepaddle 3.x 在 Windows 上 pip 安装仅支持 CPU 推理；
            # GPU 推理需在 Linux (Docker/WSL) 环境中使用 paddlepaddle-gpu。
            cuda_compiled = paddle.device.is_compiled_with_cuda()
            if cuda_compiled:
                gpu_count = paddle.device.cuda.device_count()
                if gpu_count > 0:
                    device = "gpu"
                    logger.info(
                        "检测到 CUDA GPU (共 %d 张)，使用 GPU 推理", gpu_count,
                    )
                else:
                    device = "cpu"
                    logger.warning(
                        "paddlepaddle-gpu 已安装但未检测到可用 GPU 设备，"
                        "回退 CPU 推理"
                    )
            elif await _system_has_gpu():
                device = "cpu"
                logger.warning(
                    "系统检测到 NVIDIA GPU，但 paddlepaddle 3.x 在 Windows 上"
                    "仅支持 CPU 推理。GPU 推理需在 Linux (Docker/WSL) 环境中运行，"
                    "详见 https://www.paddleocr.ai/latest/version3.x/deployment/"
                    "high_performance_inference.html"
                )
            else:
                device = "cpu"
                logger.info("未检测到系统 GPU，使用 CPU 推理")

            # 仅启用文字识别（det+rec），禁用文档方向/弯曲/行方向判定
            # 使用 PP-OCRv5 移动端模型，CPU 推理速度远快于服务端模型；
            # 紫卡截图文字清晰规整，移动端模型精度完全足够。
            # 模型自动下载到 ~/.paddlex/official_models/（paddle 默认缓存）
            #
            # enable_mkldnn=False + enable_new_ir=False 是绕过 paddle 3.x
            # Windows oneDNN PIR 属性转换错误的关键修复：
            # ConvertPirAttribute2RuntimeAttribute not support
            # [pir::ArrayAttribute<pir::DoubleAttribute>]
            self._ocr = PaddleOCR(
                lang="ch",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                device=device,
                enable_mkldnn=False,
                text_detection_model_name="PP-OCRv5_mobile_det",
                text_recognition_model_name="PP-OCRv5_mobile_rec",
                engine_config={
                    "paddle_static": {
                        "run_mode": "paddle",
                        "enable_new_ir": False,
                        "cpu_threads": 10,
                    },
                },
            )
            self._initialized = True
            logger.info(
                "PaddleOCR 引擎初始化完成（%s 推理 / paddleocr 3.x）",
                "GPU" if device == "gpu" else "CPU",
            )
        except Exception as e:
            logger.error(f"PaddleOCR 初始化失败: {e}")
            raise

    async def recognize(
        self, image: Image.Image | str
    ) -> list[dict[str, Any]]:
        """识别图片中的文字。

        Args:
            image: PIL Image 对象或图片路径。

        Returns:
            识别结果列表，每个元素包含：
            - text: 识别文字
            - confidence: 置信度
            - box: 文本框坐标 [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
        """
        if self._ocr is None:
            raise RuntimeError("OcrService 未初始化，请先调用 initialize()")

        # paddleocr 3.x 支持 ndarray / 路径，统一转 ndarray
        if isinstance(image, Image.Image):
            img_input: Any = np.array(image.convert("RGB"))
        else:
            img_input = image

        # OCR 推理是 CPU 密集型操作，在 asyncio.to_thread 中执行
        results = await asyncio.to_thread(self._ocr.predict, img_input)

        # paddleocr 3.x: 返回 list[OCRResult]，每个 OCRResult 是 dict-like
        # 携带 rec_texts / rec_scores / rec_polys
        texts: list[dict[str, Any]] = []
        if not results:
            return texts

        for page in results:
            rec_texts = page.get("rec_texts") or []
            rec_scores = page.get("rec_scores") or []
            rec_polys = page.get("rec_polys") or []
            for i, txt in enumerate(rec_texts):
                conf = float(rec_scores[i]) if i < len(rec_scores) else 0.0
                poly = rec_polys[i] if i < len(rec_polys) else None
                if poly is not None and hasattr(poly, "tolist"):
                    box = poly.tolist()
                else:
                    box = poly
                texts.append({
                    "text": txt,
                    "confidence": conf,
                    "box": box,
                })

        return texts

    async def recognize_text_only(
        self, image: Image.Image | str
    ) -> list[str]:
        """仅返回识别到的文字列表（不包含坐标和置信度）。

        Args:
            image: PIL Image 对象或图片路径。

        Returns:
            识别的文字列表。
        """
        results = await self.recognize(image)
        return [r["text"] for r in results if r["confidence"] > 0.5]
