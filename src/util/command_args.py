"""Command argument extraction / 指令参数提取

AstrBot 会把指令后的文本按空格切分，再逐个绑定到 handler 的形参上，
一个 ``str`` 形参只能拿到一个 token::

    /WM Frost Prime Set  →  keyword="Frost", is_max="Prime", is_by="Set"

凡是「名称本身可能含空格」的指令（物品名、遗物名、武器名），都不能依赖
形参绑定，必须读原始消息文本后自行解析。本模块负责剥掉开头的指令名，
返回指令之后的完整参数文本。

对齐 Go 版：``internal/onebot`` 把指令后的整段 parameter 传给 handler，
由 handler 自己用 ``strings.Fields`` / 关键字剥离处理。
"""
from __future__ import annotations

import re

from astrbot.api.event import AstrMessageEvent

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_whitespace(text: str) -> str:
    """把连续空白（含全角空格）压成单个半角空格并去掉首尾空白。"""
    return _WHITESPACE_RE.sub(" ", (text or "").strip())


def command_args(event: AstrMessageEvent, *names: str) -> str:
    """返回指令名之后的完整参数文本（空白已归一）。

    框架在唤醒阶段已去掉 ``/`` 等唤醒前缀，因此这里只需剥掉指令名本身；
    若配置了 ``wf_command_prefix``（如 ``/wf WM ...``），指令名要连同前缀一起剥。

    Args:
        event: 消息事件。
        *names: 该指令注册的名字与全部别名（不含配置前缀），
            如 ``("遗物", "核桃")``。

    Returns:
        指令名之后的文本；没有参数时返回空字符串。
    """
    text = normalize_whitespace(event.get_message_str() if event else "")
    if not text:
        return ""

    # 延迟导入：util 层不反向依赖 registry 的模块级状态（前缀是读配置得到的）
    from ...registry import command_prefix

    candidates = sorted(
        (f"{command_prefix} {name}" if command_prefix else name for name in names),
        key=len,
        reverse=True,  # 长名优先，避免 "WM" 抢在 "WMR" 之前匹配
    )
    for full_name in candidates:
        if text == full_name:
            return ""
        if text.startswith(f"{full_name} "):
            return text[len(full_name) + 1 :].strip()

    # 兜底：别名大小写与注册名不一致时，仍按「前缀 + 第一个词是指令名」处理
    if command_prefix and text.startswith(f"{command_prefix} "):
        text = text[len(command_prefix) + 1 :]
    _, sep, rest = text.partition(" ")
    return rest.strip() if sep else ""
