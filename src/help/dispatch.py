"""按钮点击 → 指令处理器路由 / Route help button clicks to command handlers

点击帮助按钮时，平台只回传 ``ButtonInteraction``（action_id + data），
不会重放一条「/平原」消息。这里把指令名映射回**原有的处理函数**并直接调用，
避免为按钮另写一套查询逻辑（也就不会出现按钮与指令行为不一致）。

AstrBot 用 ``functools.partial(handler, plugin_instance)`` 绑定处理器，
所以调用签名与框架一致：``handler(self, event)``，``self`` 就是插件实例。

Clicks arrive as a ``ButtonInteraction`` rather than a replayed command message,
so the map below calls the existing handlers directly instead of duplicating
the query logic for buttons.
"""
from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

import astrbot.api.message_components as Comp

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Sequence

#: 互动回复带不了的媒体组件；出现任一即需要改走主动发送。
#: AstrBot 在 QQ 官方互动回复里会把媒体整个丢掉（"Button interaction replies
#: currently ignore media"），剩下的空 Markdown 还会被平台拒收。
_MEDIA_COMPONENT_NAMES = ("Image", "Record", "Video", "File", "Node", "Nodes")

#: 模块级构建一次：组件类在进程生命周期内不变，避免每次调用重建元组。
_MEDIA_COMPONENTS: tuple[type, ...] = tuple(
    component
    for name in _MEDIA_COMPONENT_NAMES
    if (component := getattr(Comp, name, None)) is not None
)

#: 指令名 → ``(指令模块, 处理函数)``。
#: 只收录**无需参数**的指令：需要参数的指令点按钮时只回用法提示，
#: 不在这里登记（登记了也用不上）。键必须与 ``src/help/catalog.py``
#: 里的 ``command`` 一致（测试会校验）。
COMMAND_HANDLERS: dict[str, tuple[str, str]] = {
    "平原": ("wf_cycle", "wf_cycle"),
    "警报": ("wf_alerts", "wf_alerts"),
    "突击": ("wf_sorties", "wf_sorties"),
    "裂隙": ("wf_fissures", "wf_fissures"),
    "钢铁裂隙": ("wf_fissures", "wf_fissures_steel_path"),
    "九重天裂隙": ("wf_fissures", "wf_fissures_void_storms"),
    "奸商": ("wf_void_trader", "wf_void_trader"),
    "钢铁": ("wf_steel_path", "wf_steel_path"),
    "仲裁": ("wf_arbitration", "wf_arbitration"),
    "仲裁表": ("wf_arbitration", "wf_arbitration_table"),
    "1999": ("wf_calendar_seasons", "wf_calendar_1999"),
    "金垃圾": ("wf_market_dump", "wf_market_god_dump"),
}


def chain_has_media(chain: Sequence[object]) -> bool:
    """消息链里是否携带媒体组件 / Whether the chain carries any media.

    互动回复不能带媒体，判断结果决定按钮产出走互动回复还是主动发送。
    """
    return any(isinstance(component, _MEDIA_COMPONENTS) for component in chain)


def resolve_command_handler(command: str) -> Callable | None:
    """取指令名对应的处理函数 / Resolve the handler for a bare command name.

    Args:
        command: 不带前缀的指令名（按钮 id / 回调数据里的值）。

    Returns:
        原始（未绑定的）处理函数；未登记或模块导入失败时返回 ``None``。

    Note:
        函数内导入：``src.commands`` 包在导入时会反向导入帮助命令模块，
        顶层导入会形成循环依赖。
    """
    target = COMMAND_HANDLERS.get(command)
    if target is None:
        return None

    module_name, func_name = target
    # 延迟导入，避免 commands 包 ↔ help 包的循环依赖（导入期）
    from .. import commands as commands_pkg

    try:
        module = importlib.import_module(f"{commands_pkg.__name__}.{module_name}")
    except ImportError:
        return None
    handler = getattr(module, func_name, None)
    return handler if callable(handler) else None
