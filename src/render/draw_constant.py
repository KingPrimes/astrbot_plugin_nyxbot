"""Draw constants / 绘图常量模块

标准化绘图常量，对应 Java DrawConstants.java。
保持暗色主题风格（与现有 CardRenderer.COLORS 一致）。
"""
from __future__ import annotations

from typing import Final

# ============================================================================
# 尺寸常量 / Dimension Constants
# ============================================================================

class DrawConstant:
    """绘图常量集合 — 对应 Java DrawConstants。

    仅包含在 render 包内使用的绘图常量和工具方法。
    """

    # 底部署名文本
    FOOTER_TEXT: Final[str] = "Posted by: KingPrimes"

    # 标准图像宽度
    IMAGE_WIDTH: Final[int] = 800

    # 标准图像边距
    IMAGE_MARGIN: Final[int] = 40

    # 标准图像标题高度
    IMAGE_TITLE_HEIGHT: Final[int] = 50

    # 标准图像行高度
    IMAGE_ROW_HEIGHT: Final[int] = 50

    # 标准图像上边距
    IMAGE_MARGIN_TOP: Final[int] = 60

    # 标准图像底部高度
    IMAGE_FOOTER_HEIGHT: Final[int] = 40

    # 标准图像表头高度
    IMAGE_HEADER_HEIGHT: Final[int] = 60

    # 标准图像行边距
    IMAGE_ROW_MARGIN: Final[int] = 15

    # 标准圆角半径
    CORNER_RADIUS: Final[int] = 8

    # 帮助图像每行高度
    HELP_IMAGE_ROW_HEIGHT: Final[int] = 52

    # 帮助图像每列项目数
    HELP_IMAGE_ITEMS_PER_COLUMN: Final[int] = 22

    # 循环图像表头高度
    ALL_CYCLE_TABLE_HEADER_HEIGHT: Final[int] = 50

    # 循环图像高度
    ALL_CYCLE_HEIGHT: Final[int] = 750


# ============================================================================
# 颜色常量 / Color Constants (暗色主题)
# ============================================================================

class ThemeColor:
    """Warframe 暗色主题色板 — 与现有 CardRenderer.COLORS 保持一致。"""

    # 背景色
    BG_DARK: Final[tuple[int, int, int]] = (26, 26, 46)          # #1a1a2e
    BG_CARD: Final[tuple[int, int, int]] = (22, 33, 62)          # #16213e
    BG_CARD_ALT: Final[tuple[int, int, int]] = (30, 45, 80)      # 交替卡片背景

    # 强调色
    ACCENT: Final[tuple[int, int, int]] = (233, 69, 96)          # #e94560
    ACCENT_BLUE: Final[tuple[int, int, int]] = (69, 133, 233)    # 蓝色强调
    ACCENT_GREEN: Final[tuple[int, int, int]] = (69, 233, 150)   # 绿色强调
    ACCENT_GOLD: Final[tuple[int, int, int]] = (255, 215, 0)     # 金色

    # 文本颜色
    TEXT_PRIMARY: Final[tuple[int, int, int]] = (255, 255, 255)
    TEXT_SECONDARY: Final[tuple[int, int, int]] = (170, 170, 170)
    TEXT_MUTED: Final[tuple[int, int, int]] = (120, 120, 120)

    # 功能色
    REWARD_BG: Final[tuple[int, int, int]] = (15, 52, 96)       # 奖励标签背景
    DIVIDER: Final[tuple[int, int, int]] = (60, 60, 90)          # 分割线
    SUCCESS: Final[tuple[int, int, int]] = (69, 233, 150)
    WARNING: Final[tuple[int, int, int]] = (255, 193, 7)
    DANGER: Final[tuple[int, int, int]] = (233, 69, 96)
    INFO: Final[tuple[int, int, int]] = (69, 133, 233)

    # 循环图像颜色
    CYCLE_WARM: Final[tuple[int, int, int]] = (255, 128, 0)
    CYCLE_COLD: Final[tuple[int, int, int]] = (0, 180, 255)

    # 表格颜色
    TABLE_HEADER_BG: Final[tuple[int, int, int]] = (41, 128, 185)  # #2980b9
    TABLE_EVEN_ROW: Final[tuple[int, int, int]] = (22, 33, 62)     # 与 BG_CARD 一致
    TABLE_BORDER: Final[tuple[int, int, int]] = (60, 60, 90)

    # 帮助图像
    HELP_HEADER_BG: Final[tuple[int, int, int]] = (41, 128, 185)
    HELP_EVEN_ROW: Final[tuple[int, int, int]] = (248, 249, 250)  # 亮色（仅帮助图）

    # 裂隙任务时间颜色
    TIME_LOW: Final[tuple[int, int, int]] = (255, 107, 107)       # 红色 - 时间紧急
    TIME_MEDIUM: Final[tuple[int, int, int]] = (170, 126, 30)     # 黄色 - 时间适中
    TIME_HIGH: Final[tuple[int, int, int]] = (29, 209, 161)       # 绿色 - 时间充足

    # Void Tiers
    VOID_T1: Final[tuple[int, int, int]] = (81, 66, 52)
    VOID_T2: Final[tuple[int, int, int]] = (117, 86, 43)
    VOID_T3: Final[tuple[int, int, int]] = (159, 158, 158)
    VOID_T4: Final[tuple[int, int, int]] = (193, 190, 57)
    VOID_T5: Final[tuple[int, int, int]] = (135, 42, 44)


# ============================================================================
# 工具函数 / Utility Functions
# ============================================================================

def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """将十六进制颜色字符串转换为 RGB 元组。

    支持格式: "#RRGGBB"、"RRGGBB"。

    Args:
        hex_color: 十六进制颜色字符串。

    Returns:
        (R, G, B) 元组，每个分量 0-255。
    """
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        raise ValueError(f"无效的十六进制颜色: {hex_color!r}，需要 6 位十六进制")
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    """将 RGB 元组转换为十六进制颜色字符串。

    Args:
        rgb: (R, G, B) 元组。

    Returns:
        带 # 前缀的十六进制颜色字符串。
    """
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


def lerp_color(
    a: tuple[int, int, int],
    b: tuple[int, int, int],
    t: float,
) -> tuple[int, int, int]:
    """在两个 RGB 颜色之间线性插值。

    Args:
        a: 起始颜色。
        b: 终止颜色。
        t: 插值因子，0.0 = a, 1.0 = b。

    Returns:
        插值后的 RGB 颜色。
    """
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )
