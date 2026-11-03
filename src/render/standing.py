"""看板娘立绘共享模块

提供按季节选取和绘制看板娘立绘的公共函数。
所有需要右下角看板娘装饰的卡片渲染器均可调用。

立绘编号（`styles/` 目录）：

| 编号 | 用途 |
| --- | --- |
| 1 | 默认（常服），季节图缺失时兜底 |
| 2 | 春季 |
| 3 | 夏季 |
| 4 | 秋季 |
| 5 | 冬季 |

默认所有卡片都会跟随本机当前日期自动换季；把 `SEASONAL_STANDING`
置为 `False` 可让全部卡片固定使用默认立绘。
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from PIL import Image

from .image_combiner import ImageCombiner

# 看板娘最大尺寸 — 对应 Java: imageWidth=413, imageHeight=625
STANDING_MAX_W = 413
STANDING_MAX_H = 625

# 看板娘目录
STANDING_DIR: Path = Path(__file__).parent / "styles"

# 默认立绘编号（1.png）
DEFAULT_STANDING_INDEX = 1

SPRING = "spring"
SUMMER = "summer"
AUTUMN = "autumn"
WINTER = "winter"

# 季节 → 立绘编号（北半球节气：3-5 春 / 6-8 夏 / 9-11 秋 / 12-2 冬）
SEASON_STANDING_INDEX: dict[str, int] = {
    SPRING: 2,
    SUMMER: 3,
    AUTUMN: 4,
    WINTER: 5,
}

SEASON_LABELS: dict[str, str] = {
    SPRING: "春季",
    SUMMER: "夏季",
    AUTUMN: "秋季",
    WINTER: "冬季",
}

# 季节别名归一化：兼容中文、英文小写与 1999 日历的 CST_* 枚举名
_SEASON_ALIASES: dict[str, str] = {
    "spring": SPRING,
    "春季": SPRING,
    "cst_spring": SPRING,
    "summer": SUMMER,
    "夏季": SUMMER,
    "cst_summer": SUMMER,
    "autumn": AUTUMN,
    "秋季": AUTUMN,
    "fall": AUTUMN,
    "cst_fall": AUTUMN,
    "winter": WINTER,
    "冬季": WINTER,
    "cst_winter": WINTER,
}

# 是否按现实季节自动换装；关闭后所有卡片固定使用默认立绘
SEASONAL_STANDING = True

# 模块级缓存：按编号缓存立绘，避免每次渲染都从磁盘读取
_index_cache: dict[int, Image.Image] = {}


def _load_image_safe(png_path: Path) -> Image.Image | None:
    try:
        img = Image.open(png_path)
        img.load()
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        return img
    except Exception:
        return None


def _load_index(index: int) -> Image.Image | None:
    """按编号加载立绘（带内存缓存）。"""
    if index in _index_cache:
        return _index_cache[index]
    img = _load_image_safe(STANDING_DIR / f"{index}.png")
    if img is not None:
        _index_cache[index] = img
    return img


def current_season(today: date | None = None) -> str:
    """返回本机当前日期对应的季节标识。"""
    month = (today or datetime.now().date()).month
    if month in (3, 4, 5):
        return SPRING
    if month in (6, 7, 8):
        return SUMMER
    if month in (9, 10, 11):
        return AUTUMN
    return WINTER


def resolve_standing_index(seasonal: bool | None = None) -> int:
    """解析当前应使用的立绘编号。

    Args:
        seasonal: `True` 跟随季节，`False` 固定默认立绘，
            `None` 时取模块开关 `SEASONAL_STANDING`。
    """
    if seasonal is None:
        seasonal = SEASONAL_STANDING
    if not seasonal:
        return DEFAULT_STANDING_INDEX
    return SEASON_STANDING_INDEX.get(current_season(), DEFAULT_STANDING_INDEX)


def normalize_season(value: object) -> str | None:
    """把各种季节写法归一化为季节标识。

    支持 `None`、`"夏季"`、`"CST_SUMMER"`、`SeasonEnum.CST_SUMMER` 等。

    Returns:
        季节标识（spring/summer/autumn/winter）；无法识别时返回 `None`。
    """
    if value is None:
        return None
    raw = getattr(value, "value", value)  # 枚举取中文值
    if not isinstance(raw, str):
        return None
    key = raw.strip()
    if not key:
        return None
    return _SEASON_ALIASES.get(key.lower())


def standing_index_for_season(season: object) -> int:
    """按**数据里的季节**返回立绘编号（季节为空或无法识别时用默认立绘）。

    1999 日历这类卡片应按游戏内季节换装，而不是本机日期。
    """
    key = normalize_season(season)
    if key is None:
        return DEFAULT_STANDING_INDEX
    return SEASON_STANDING_INDEX.get(key, DEFAULT_STANDING_INDEX)


def pick_standing_image(
    seasonal: bool | None = None,
    index: int | None = None,
) -> Image.Image | None:
    """选取看板娘立绘（无磁盘 I/O，命中缓存）。

    Args:
        seasonal: 是否跟随季节，`None` 取模块开关。
        index: 显式指定立绘编号，优先级高于 `seasonal`。

    Returns:
        立绘图片；缺失季节图时回退默认立绘，全部缺失返回 `None`。
    """
    if index is not None:
        return _load_index(index) or _load_index(DEFAULT_STANDING_INDEX)

    img = _load_index(resolve_standing_index(seasonal))
    if img is None:
        img = _load_index(DEFAULT_STANDING_INDEX)
    return img


def resize_fit(img: Image.Image, max_w: int, max_h: int) -> tuple[int, int]:
    """等比例缩放，返回 (w, h)。"""
    ratio = min(max_w / img.width, max_h / img.height, 1.0)
    return int(img.width * ratio), int(img.height * ratio)


def draw_standing(
    cb: ImageCombiner,
    max_w: int | None = None,
    max_h: int | None = None,
    seasonal: bool | None = None,
    index: int | None = None,
) -> None:
    """右下角绘制看板娘立绘 — 对应 Java drawStandingDrawing()。

    若未指定 max_w/max_h，自动根据画布高度选择缩放尺寸：
      画布高度 <= STANDING_MAX_H → 缩小版 (240x360)
      画布高度 >  STANDING_MAX_H → 标准版 (413x625)

    若指定了 max_w/max_h，则按给定尺寸等比例缩放。

    Args:
        seasonal: 是否跟随现实季节换装，`None` 取模块开关。
        index: 显式指定立绘编号（优先级最高），用于按数据季节换装的卡片。
    """
    img = pick_standing_image(seasonal, index)
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
    seasonal: bool | None = None,
    index: int | None = None,
) -> None:
    """在指定位置绘制缩放的看板娘立绘。

    不同于 draw_standing 的右下角自动定位，
    本函数支持指定绝对坐标和最大尺寸。

    Args:
        seasonal: 是否跟随现实季节换装，`None` 取模块开关。
        index: 显式指定立绘编号（优先级最高）。
    """
    img = pick_standing_image(seasonal, index)
    if img is None:
        return

    target_w, target_h = resize_fit(img, max_w, max_h)
    img_resized = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    if img_resized.mode != "RGBA":
        img_resized = img_resized.convert("RGBA")
    cb.draw_image(img_resized, x, y)
