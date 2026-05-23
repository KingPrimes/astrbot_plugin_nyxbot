"""
VallisCycle Model / 奥布山谷冷暖循环模型

对应 Java: VallisCycle.java
基于 2018-11-10T08:13:48Z 起始时间 + 1600s 周期推算温暖/寒冷（温暖 400s / 寒冷 1200s）。

不继承 BastWorldState，是纯计算模型。

参考: https://github.com/WFCD/warframe-worldstate-parser
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from ...util.time_utils import time_delta_to_string

# 起始纪元时间（毫秒）/ Start epoch (milliseconds) — 2018-11-10T08:13:48Z
_L_START_MS: int = 1541837628000
# 总周期时长（毫秒）/ Total loop time (milliseconds)
_LOOP_TIME: int = 1_600_000
# 温暖期持续时间（毫秒）/ Warm time duration (milliseconds)
_WARM_TIME: int = 400_000
# 寒冷期持续时间（毫秒）/ Cold time duration (milliseconds)
_COLD_TIME: int = _LOOP_TIME - _WARM_TIME


class VallisCycle:
    """奥布山谷冷暖循环 / Orb Vallis Warm/Cold Cycle

    对应 Java: VallisCycle
    温暖 400s → 寒冷 1200s，每 1600s 一个完整周期。
    """

    def __init__(self) -> None:
        now_ms = int(time.time() * 1000)
        since_last = (now_ms - _L_START_MS) % _LOOP_TIME
        to_next_full = _LOOP_TIME - since_last

        state: str
        if to_next_full > _COLD_TIME:
            state = "温暖"
        else:
            state = "寒冷"

        to_next_minor: int
        if to_next_full < _COLD_TIME:
            to_next_minor = to_next_full
        else:
            to_next_minor = to_next_full - _COLD_TIME

        time_at_next_ms = now_ms + to_next_minor
        time_at_previous_ms = now_ms + to_next_full - (_LOOP_TIME if state == "温暖" else _COLD_TIME)

        self.state: str = state
        self.is_warm: bool = state == "温暖"
        self.expiry: datetime = datetime.fromtimestamp(time_at_next_ms / 1000, tz=timezone.utc)
        self.activation: datetime = datetime.fromtimestamp(time_at_previous_ms / 1000, tz=timezone.utc)
        self.time_left: str = time_delta_to_string(to_next_minor)
        self.expired: bool = self.expiry < datetime.now(timezone.utc)
