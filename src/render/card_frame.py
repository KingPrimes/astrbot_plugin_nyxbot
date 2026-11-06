"""卡片骨架 / Card frame helpers

把「每张卡都要画、且必须一致」的部分收口到一处：

* 画布与卡面 —— ``components.new_page``（圆角 + 1px 边框）
* 页头 —— ``components.draw_header``（大标题 + 副标题 + 分割线）
* 看板娘 —— 内容下方右对齐，避免压字
* 页脚署名 —— 读品牌设置（``render_branding.json``），关闭时不画

新迁移的卡片只需要准备数据、选一个内容块（kv / table / grid），
再调 :func:`draw_standing_block` / :func:`draw_footer_block`。

高度一律「先量后建页」：

    height = C.content_top() + header_h + body_h + standing_h + C.footer_space()

其中 ``standing_h`` 用 :func:`standing_block_height`，``C.footer_space()`` 已含页脚行高。
"""
from __future__ import annotations

from . import components as C
from .branding import signature_text, standing_size as _branding_standing_size
from .design import SPACE
from .standing import (
    draw_standing_at,
    pick_standing_image,
    resize_fit,
    standing_index_for_season,
)

#: 看板娘尺寸档位（与 branding.STANDING_SIZES 同一份）。
STANDING_SIZES: dict[str, tuple[int, int]] = {
    "sm": (200, 300),
    "md": (280, 420),
    "lg": (360, 540),
}


def resolve_standing_size(size: str | None = None) -> tuple[int, int]:
    """解析尺寸档位；``None`` 取品牌设置。"""
    if size is None:
        return _branding_standing_size()
    return STANDING_SIZES.get(size, STANDING_SIZES["md"])


def standing_block_height(
    size: str | None = None,
    content_w: int = 9999,
    season: str | None = None,
) -> int:
    """看板娘块占用的高度（含与内容的呼吸间距）；关闭或素材缺失时返回 0。

    Args:
        season: 数据里的季节（如 1999 日历的 ``spring``）；给了就按它换装，
            不跟随本机日期。
    """
    image = pick_standing_image(index=standing_index_for_season(season) if season else None)
    if image is None:
        return 0
    max_w, max_h = resolve_standing_size(size)
    _, height = resize_fit(image, min(max_w, content_w), max_h)
    return height + SPACE["xl"]


def draw_standing_block(
    page,
    y: int,
    size: str | None = None,
    season: str | None = None,
) -> int:
    """在内容下方画看板娘（右对齐），返回占用后的 y。"""
    image = pick_standing_image(index=standing_index_for_season(season) if season else None)
    if image is None:
        return y

    max_w, max_h = resolve_standing_size(size)
    width, height = resize_fit(image, min(max_w, page.content_w), max_h)
    draw_standing_at(
        page.cb,
        page.content_x + page.content_w - width,
        y + SPACE["xl"],
        width,
        height,
    )
    return y + height + SPACE["xl"]


def standing_cell_size(max_w: int, max_h: int) -> tuple[int, int]:
    """把看板娘缩进一个网格空位，返回 (宽, 高)；禁用或素材缺失返回 (0, 0)。"""
    image = pick_standing_image()
    if image is None:
        return 0, 0
    return resize_fit(image, max_w, max_h)


def draw_standing_in_cell(page, x: int, y: int, max_w: int, max_h: int) -> int:
    """在网格空位里画看板娘（水平居中），返回实际高度；放不下返回 0。"""
    width, height = standing_cell_size(max_w, max_h)
    if not height:
        return 0
    draw_standing_at(page.cb, x + (max_w - width) // 2, y, width, height)
    return height


def footer_text(text: str = "") -> str:
    """页脚文案：显式文本优先，空则取全局署名，关闭时为空串。"""
    return (text or "").strip() or signature_text()


def draw_footer_block(page, text: str = "") -> None:
    """画页脚署名；无文案（全局关闭）时什么都不画。"""
    content = footer_text(text)
    if content:
        C.draw_footer(page, content)
