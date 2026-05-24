"""看板娘立绘共享模块

提供随机选取和绘制看板娘立绘的公共函数。
所有需要右下角看板娘装饰的卡片渲染器均可调用。
"""
from __future__ import annotations

import random
from pathlib import Path

from PIL import Image

from .image_combiner import ImageCombiner

# 看板娘最大尺寸 — 对应 Java: imageWidth=413, imageHeight=625
STANDING_MAX_W = 413
STANDING_MAX_H = 625

# 看板娘目录
STANDING_DIR: Path = Path(__file__).parent / "styles"


def pick_standing_image() -> Image.Image | None:
    """随机选择一张看板娘图片 / Randomly pick a standing drawing."""
    if not STANDING_DIR.exists():
        return None
    pngs = sorted(STANDING_DIR.glob("*.png"))
    if not pngs:
        return None
    chosen = random.choice(pngs)
    return Image.open(chosen)


def resize_fit(img: Image.Image, max_w: int, max_h: int) -> tuple[int, int]:
    """等比例缩放，返回 (w, h)。"""
    ratio = min(max_w / img.width, max_h / img.height, 1.0)
    return int(img.width * ratio), int(img.height * ratio)


def draw_standing(
    cb: ImageCombiner,
    max_w: int | None = None,
    max_h: int | None = None,
) -> None:
    """右下角绘制看板娘立绘 — 对应 Java drawStandingDrawing()。

    若未指定 max_w/max_h，自动根据画布高度选择缩放尺寸：
      画布高度 <= STANDING_MAX_H → 缩小版 (240x360)
      画布高度 >  STANDING_MAX_H → 标准版 (413x625)

    若指定了 max_w/max_h，则按给定尺寸等比例缩放。
    """
    img = pick_standing_image()
    if img is None:
        return

    if max_w is not None and max_h is not None:
        # 自定义尺寸
        target_w, target_h = resize_fit(img, max_w, max_h)
        x = cb.width - target_w - 25
        y = cb.height - target_h - 22
    elif cb.height <= STANDING_MAX_H:
        # 缩小版 — 对应 Java drawOneInchStandingDrawing()
        max_w_s, max_h_s = 240, 360
        target_w, target_h = resize_fit(img, max_w_s, max_h_s)
        x = cb.width - 265
        if target_w < max_w_s:
            x = cb.width - target_w - 25
        y = cb.height - 382
        if target_h < max_h_s:
            y = cb.height - target_h - 22
    else:
        # 标准版
        target_w, target_h = resize_fit(img, STANDING_MAX_W, STANDING_MAX_H)
        x = cb.width - 433
        if target_w < STANDING_MAX_W:
            x = cb.width - target_w - 20
        y = cb.height - 645
        if target_h < STANDING_MAX_H:
            y = cb.height - target_h - 20

    img_resized = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    if img_resized.mode != "RGBA":
        img_resized = img_resized.convert("RGBA")
    cb.draw_image(img_resized, x, y)


def draw_standing_at(
    cb: ImageCombiner,
    x: int,
    y: int,
    max_w: int,
    max_h: int,
) -> None:
    """在指定位置绘制缩放的看板娘立绘。

    不同于 draw_standing 的右下角自动定位，
    本函数支持指定绝对坐标和最大尺寸。
    """
    img = pick_standing_image()
    if img is None:
        return

    target_w, target_h = resize_fit(img, max_w, max_h)
    img_resized = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    if img_resized.mode != "RGBA":
        img_resized = img_resized.convert("RGBA")
    cb.draw_image(img_resized, x, y)
