"""Whisper entry model / 私聊语句模型

一条订单/拍卖对应的游戏内私聊语句（``/w 玩家名 你好! ...``）。
生成逻辑在 ``src/service/whisper.py``，这里只定义数据结构，供各响应模型引用。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class WhisperEntry:
    """一条可直接粘贴到游戏内的私聊语句。"""

    ingame_name: str
    """卖家游戏内名称（``/w`` 后面那个）。"""

    locale: str = field(default="")
    """卖家语言偏好（原始 locale，便于排障）。"""

    lang: str = field(default="zh")
    """实际使用的模板语言：``zh`` / ``en``。"""

    status: str = field(default="")
    """卖家在线状态（online / ingame / offline）。"""

    text: str = field(default="")
    """完整语句，形如 ``/w xxx 你好! 我想以20白金购买: "..."。``"""

    def __str__(self) -> str:  # 方便日志与调试
        return self.text
