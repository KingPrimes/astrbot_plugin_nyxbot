"""
EarthCycle Model / 地球昼夜循环模型

对应 Java: EarthCycle.java
基于系统时间 + 28800s 周期（白天 4h / 夜晚 4h）通过数学推算昼夜。

不继承 BastWorldState，是纯计算模型（不从 JSON 反序列化）。

参考: https://github.com/WFCD/warframe-worldstate-parser
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from ...util.time_utils import time_delta_to_string

# 地球周期总时长（秒）/ Earth cycle total duration (seconds)
_CYCLE_SECONDS: int = 28800
# 白天最大持续时间（秒）/ Daytime max duration (seconds)
_DAYTIME_LIMIT: int = 14400


class EarthCycle:
    """地球昼夜循环 / Earth Day/Night Cycle

    对应 Java: EarthCycle
    白天 4 小时 → 夜晚 4 小时，每 8 小时一个完整周期。
    """

    def __init__(self) -> None:
        now_ms = int(time.time() * 1000)
        now_seconds = now_ms // 1000

        cycle_seconds = now_seconds % _CYCLE_SECONDS
        self.is_day: bool = cycle_seconds < _DAYTIME_LIMIT

        seconds_left = _DAYTIME_LIMIT - (cycle_seconds % _DAYTIME_LIMIT)
        millis_left = seconds_left * 1000

        expiry_ms = now_ms + millis_left
        self.expiry: datetime = datetime.fromtimestamp(expiry_ms / 1000, tz=timezone.utc)

        # 圆整到分钟 / Round to minute
        minutes_coef = 1000 * 60
        rounded_ms = round(float(now_ms + millis_left) / minutes_coef) * minutes_coef
        self.rounded: datetime = datetime.fromtimestamp(rounded_ms / 1000, tz=timezone.utc)

        self.time_left: str = time_delta_to_string(millis_left)
        self.state: str = "白昼" if self.is_day else "夜晚"

        # 开始时间为结束时间前 4 小时 / Start is 4 hours before expiry
        self.start: datetime = self.expiry - timedelta(hours=4)
        self.activation: datetime = self.start

        self.expired: bool = self.expiry < datetime.now(timezone.utc)
