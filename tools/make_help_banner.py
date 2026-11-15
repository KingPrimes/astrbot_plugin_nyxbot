"""生成帮助消息顶部的居中 Logo 横幅 / Build the centered logo banner.

QQ 官方 Markdown 不支持对齐语法，图片只会左对齐。变通方案：
把 logo 居中贴到一张**透明底横幅**上，图片铺满消息框宽度时，
logo 看起来就是居中的。

产物：仓库根目录 ``banner.png``（2 倍尺寸，配合 `#440px #110px` 显示），
经 jsDelivr 引用（见 ``_conf_schema.json`` 的 ``wf_help_logo_url``）。

用法::

    uv run python tools/make_help_banner.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

#: 横幅画布（2 倍图，显示时按 440x110）。
CANVAS_SIZE = (880, 220)

#: Logo 显示尺寸（画布内的实际像素）。
LOGO_SIZE = 176


def main() -> None:
    logo = Image.open(ROOT / "logo.png").convert("RGBA").resize(
        (LOGO_SIZE, LOGO_SIZE), Image.LANCZOS
    )
    canvas = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    canvas.alpha_composite(
        logo,
        ((CANVAS_SIZE[0] - LOGO_SIZE) // 2, (CANVAS_SIZE[1] - LOGO_SIZE) // 2),
    )
    out = ROOT / "banner.png"
    canvas.save(out)
    print(f"已生成 {out} ({CANVAS_SIZE[0]}x{CANVAS_SIZE[1]}, logo 居中)")


if __name__ == "__main__":
    main()
