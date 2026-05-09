"""OCR Service / PaddleOCR 文字识别服务

使用 PaddleOCR PP-OCRv5 进行 CPU 推理，仅启用文字识别（det+rec）。
"""
from __future__ import annotations

import asyncio
from typing import Any, Optional

import numpy as np
from PIL import Image
from astrbot.api import logger


class OcrService:
    """PaddleOCR 文字识别服务（CPU 推理，仅文字识别）。

    单例模式，延迟初始化 OCR 引擎。
    """

    _instance: Optional[OcrService] = None
    _ocr: Any = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self) -> None:
        """延迟初始化 OCR 引擎。

        首次调用时下载并加载 PP-OCRv5 模型。
        """
        if self._initialized:
            return

        try:
            from paddleocr import PaddleOCR

            # CPU 推理，仅启用文字识别（det+rec），禁用无用模块
            self._ocr = PaddleOCR(
                use_angle_cls=False,   # 无需方向分类
                lang="ch",             # 中英文模型
                use_gpu=False,         # CPU 推理
                show_log=False,        # 静默模式
                det_model_dir=None,    # 使用默认模型（自动下载 PP-OCRv5）
                rec_model_dir=None,
            )
            self._initialized = True
            logger.info("PaddleOCR 引擎初始化完成（CPU 推理）")
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
        if not self._initialized:
            await self.initialize()

        # 确保输入为 numpy array
        if isinstance(image, Image.Image):
            img_array = np.array(image.convert("RGB"))
        else:
            img_array = image  # str path

        # OCR 推理是 CPU 密集型操作，在 asyncio.to_thread 中执行
        result = await asyncio.to_thread(self._ocr.ocr, img_array, cls=False)

        # 解析结果
        texts: list[dict[str, Any]] = []
        if result and result[0]:
            for line in result[0]:
                box, (text, confidence) = line
                texts.append({
                    "text": text,
                    "confidence": float(confidence),
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
