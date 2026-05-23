"""
CetusCycle Model / 夜灵平原昼夜循环模型

对应 Java: CetusCycle.java
依赖 SyndicateMission(CetusSyndicate).expiry 的毫秒时间戳，
基于赏金结束时间推算 150min 昼夜（白天 100min / 夜晚 50min）。

不继承 BastWorldState，是纯计算模型。

参考: https://github.com/WFCD/warframe-worldstate-parser
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from ...util.time_utils import time_delta_to_string

# 夜晚持续时间（秒）/ Night duration (seconds)
_NIGHT_TIME: int = 3000
# 各状态最大持续时间（毫秒）/ Maximum duration per state (milliseconds)
_MAXIMUMS: dict[str, int] = {
    "白昼": 6_000_000,
    "夜晚": 3_000_000,
}


class CetusCycle:
    """夜灵平原昼夜循环 / Cetus (Plains of Eidolon) Day/Night Cycle

    对应 Java: CetusCycle
    白天 100 分钟 → 夜晚 50 分钟。
    构造时需传入 CetusSyndicate 赏金任务的 expiry 毫秒时间戳。
    """

    def __init__(self, bounties_end_ms: int) -> None:
        """
        Args:
            bounties_end_ms: CetusSyndicate 赏金任务 expiry 的毫秒时间戳
                             (from SyndicateMission.expiry.time_millis)
        """
        now_ms = int(time.time() * 1000)

        millis_left = bounties_end_ms - now_ms
        seconds_to_night_end = round(millis_left / 1000)
        day_time = seconds_to_night_end > _NIGHT_TIME

        seconds_remaining_in_cycle = seconds_to_night_end - _NIGHT_TIME if day_time else seconds_to_night_end
        millis_left = seconds_remaining_in_cycle * 1000

        minutes_coef = 1000 * 60
        expiry_ms = now_ms + round(float(millis_left) / minutes_coef) * minutes_coef
        expiry = datetime.fromtimestamp(expiry_ms / 1000, tz=timezone.utc)

        state = "白昼" if day_time else "夜晚"

        max_ms = _MAXIMUMS[state]
        activation = datetime.fromtimestamp((expiry_ms - max_ms) / 1000, tz=timezone.utc)

        self.is_day: bool = day_time
        self.expiry: datetime = expiry
        self.activation: datetime = activation
        self.state: str = state
        self.cycle: str = "day" if day_time else "night"
        self.time_left: str = time_delta_to_string(millis_left)
