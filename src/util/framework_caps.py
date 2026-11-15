"""AstrBot 框架能力探测 / Framework capability probes

按钮交互依赖两件**相互独立**的框架能力：

1. 消息组件：``Comp.Button`` / ``Comp.ActionRow``（构造键盘用）；
2. 回调注册：``filter.button_action``（较新版本才有的装饰器，接收点击）。

旧版 AstrBot 可能只有组件没有回调装饰器——若只探测组件就发按钮，
用户会看到「点了没反应」的死按钮（2026-11-16 Sourcery 评审 #6）。
因此构建按钮前必须同时确认两者，统一从本模块取探测结果，
不要在各自模块里重复 ``hasattr`` 探测。

探测必须是**防御式**的：能力残缺的框架（甚至只有部分子模块的桩）上
导入本模块都不能崩，这正是本模块存在的意义——所以不用
``from astrbot.api.event import filter`` 硬导入，而是 ``getattr`` 逐层探测。

Button interaction needs BOTH the message components and the callback
decorator; probe once here (defensively) and share the verdict.
"""
from __future__ import annotations

import astrbot.api.event as _event_module
import astrbot.api.message_components as Comp

#: 是否存在按钮消息组件（``Comp.Button`` / ``Comp.ActionRow``）。
BUTTON_COMPONENTS_AVAILABLE: bool = hasattr(Comp, "Button") and hasattr(
    Comp, "ActionRow"
)

#: 是否支持按钮回调注册（``filter.button_action`` 装饰器）。
BUTTON_ACTION_AVAILABLE: bool = (
    getattr(getattr(_event_module, "filter", None), "button_action", None)
    is not None
)

#: 按钮端到端可用（组件 + 回调注册齐备）；缺任一环都不应发送按钮。
BUTTONS_AVAILABLE: bool = BUTTON_COMPONENTS_AVAILABLE and BUTTON_ACTION_AVAILABLE
