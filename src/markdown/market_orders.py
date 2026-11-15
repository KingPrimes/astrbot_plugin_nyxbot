"""市场订单 Markdown 格式化器 / Market Orders Markdown Formatter

WM（``/WM``）订单结果以 Markdown 表格回复（CD/XT/WR 后续复用）。
2026-11-16 用 ``/表格测试`` 实测：QQ 官方自定义 Markdown **已支持表格**
（标准 / 紧凑写法、引用块内嵌均可正常渲染，官方文档已过时），因此订单
列表直接用真实表格输出，列结构对齐图片卡片。

表格列（对齐 ``card_market_orders`` 图片卡片）：
``序号 | 价格 | 数量 | 等级 | 卖家 | 状态``；空值显示 ``-``。

状态色点（Markdown 无法上色，用 emoji 区分）：🟢在线 / 🔵游戏中 /
🔴离线 / ❔隐身。

序号与 ``/w 序号`` 的取用一一对应：私聊语句由 ``whisper_service`` 按
（会话, 发送者）缓存 2 分钟，卡片底部的序号按钮与 ``/w`` 指令走同一份
缓存（见 ``src/util/whisper_buttons.py`` 与 ``wf_whisper``）。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..model.market.market_orders import Orders

#: 状态 → 「色点 + 文字」。文字保留（用户反馈只看图标认不准确）。
_STATUS_STYLES: dict[str, str] = {
    "online": "🟢在线",
    "ingame": "🔵游戏中",
    "offline": "🔴离线",
    "invisible": "❔隐身",
}


def _number_badge(index: int) -> str:
    """序号 → 键帽 emoji（1️⃣..8️⃣）/ Row number as a keycap emoji.

    键帽 emoji 比圆圈数字（①②…）大且带底色框，手机上更好分辨
    （用户反馈）；``orders.orders`` 上限 8 条，超出回落纯数字。
    """
    if index < 8:
        return f"{index + 1}\ufe0f\u20e3"
    return str(index + 1)

#: 表格空值占位。
_EMPTY_CELL = "-"


def _status_text(status: object) -> str:
    """状态枚举 → 「色点 + 文字」/ Status → emoji + label."""
    key = str(getattr(status, "value", status) or "").lower()
    return _STATUS_STYLES.get(key, "❔未知")


def _order_row(index: int, order) -> str:
    """一行订单表格 / One table row for an order."""
    price = f"{order.platinum}p" if order.platinum is not None else _EMPTY_CELL
    quantity = str(order.quantity) if order.quantity else _EMPTY_CELL
    rank = str(order.rank) if order.rank is not None else _EMPTY_CELL
    user = order.user
    seller = (user.ingame_name if user else None) or _EMPTY_CELL
    status = _status_text(user.status) if user else "❔未知"
    return (
        f"| {_number_badge(index)} | {price} | {quantity} | {rank} "
        f"| {seller} | {status} |"
    )


def format_orders_markdown(orders: Orders, with_buttons: bool = False) -> str:
    """把订单结果格式化为 Markdown 表格 / Format orders as a Markdown table.

    Args:
        orders: ``MarketOrdersService.search_market_orders`` 返回的渲染模型。
        with_buttons: 消息是否附带序号取句按钮——影响提示语文案
            （按钮缺席时提示用 ``/w 序号``）。

    Returns:
        可直接放进 ``Comp.Plain`` 的 Markdown 文本。
    """
    info = [
        f"平台 {(orders.form or 'pc').upper()}",
        "买家订单" if orders.is_by else "卖家订单",
        f"共 {len(orders.orders)} 条",
    ]
    if orders.trading_tax:
        info.append(f"交易税 {orders.trading_tax:,}")
    if orders.ducats:
        info.append(f"杜卡币 {orders.ducats:,}")

    lines: list[str] = [
        f"# {orders.name}",
        "> " + " · ".join(info),
        "> "
        + (
            "点击下方序号按钮获取私聊语句，长按复制"
            if with_buttons
            else "回复 /w 序号 获取对应卖家的私聊语句（2 分钟内有效）"
        ),
        "",
        "| 序号 | 价格 | 数量 | 等级 | 卖家 | 状态 |",
        "| --- | --- | --- | --- | --- | --- |",
        *(
            _order_row(index, order)
            for index, order in enumerate(orders.orders)
        ),
    ]

    # 去掉结尾多余空行
    while lines and not lines[-1]:
        lines.pop()

    return "\n".join(lines)
