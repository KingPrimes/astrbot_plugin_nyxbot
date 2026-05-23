"""
DuvalierCycle Model / 双衍王境情绪循环模型

对应 Java: DuvalierCycle.java
基于 36000s 周期 / 5 情绪状态（悲伤→恐惧→喜悦→愤怒→嫉妒），每状态 7200s。
依赖 EndlessXpChoices 列表（可选内容）。

不继承 BastWorldState，是纯计算模型。

参考: https://github.com/WFCD/warframe-worldstate-parser
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from ...util.time_utils import time_delta_to_string

if TYPE_CHECKING:
    from .endless_xp_choices import EndlessXpChoices

# 总周期时长（秒）/ Total cycle time (seconds)
_CYCLE_TIME: int = 36000
# 每个阶段持续时间（秒）/ Duration per state (seconds)
_STATE_TIME: int = 7200
# 5 种情绪状态 / 5 emotional states
_STATES: list[str] = ["悲伤", "恐惧", "喜悦", "愤怒", "嫉妒"]


class DuvalierCycle:
    """双衍王境情绪循环 / Duviri Mood Cycle

    对应 Java: DuvalierCycle
    5 种情绪循环，每 2 小时切换一次，10 小时完整周期。
    """

    def __init__(self, choices: list[EndlessXpChoices] | None = None) -> None:
        """
        Args:
            choices: 当前循环可选内容列表，从 WorldState.endless_xp_choices 获取
        """
        self.choices: list[EndlessXpChoices] | None = choices

        now_seconds = int(time.time())
        cycle_delta = (now_seconds - 52) % _CYCLE_TIME
        state_ind = cycle_delta // _STATE_TIME
        state_delta = cycle_delta % _STATE_TIME
        until_next = _STATE_TIME - state_delta

        self.state: str = _STATES[state_ind]

        self.expiry = datetime.now(timezone.utc) + timedelta(seconds=until_next)
        self.activation = self.expiry - timedelta(seconds=_STATE_TIME)
        self.time_left: str = time_delta_to_string(
            int(self.expiry.timestamp() * 1000) - int(time.time() * 1000)
        )
