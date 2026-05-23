"""
ZarimanCycle Model / 扎里曼轮换循环模型

对应 Java: ZarimanCycle.java
基于 Corpus 起始时间 (2022-06-14T05:00:00Z) + 18000s 周期
推算 Grineer/Corpus 轮换（各 9000s）。

依赖 SyndicateMission(ZarimanSyndicate).expiry 的毫秒时间戳。

不继承 BastWorldState，是纯计算模型。

参考: https://github.com/WFCD/warframe-worldstate-parser
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from ...util.time_utils import time_delta_to_string

# Corpus 起始时间（毫秒）/ Corpus start time (milliseconds) — 2022-06-14T05:00:00Z
_CORPUS_TIME_MILLIS: int = 1_655_182_800_000
# 完整周期时长（毫秒）/ Full cycle duration (milliseconds)
_FULL_CYCLE: int = 18_000_000
# 每个阶段最大持续时间（毫秒）/ Maximum duration per state (milliseconds)
_STATE_MAXIMUM: int = 9_000_000


class ZarimanCycle:
    """扎里曼轮换循环 / Zariman Rotation Cycle

    对应 Java: ZarimanCycle
    Grineer/Corpus 轮换，各 9000s，完整周期 18000s。
    构造时需传入 ZarimanSyndicate 赏金任务的 expiry 毫秒时间戳。
    """

    def __init__(self, bounties_end_ms: int) -> None:
        """
        Args:
            bounties_end_ms: ZarimanSyndicate 赏金任务 expiry 的毫秒时间戳
                             (from SyndicateMission.expiry.time_millis)
        """
        now_ms = int(time.time() * 1000)

        # 计算剩余时间 / Calculate time left
        bounties_clone = bounties_end_ms - 5000
        millis_left = bounties_clone - now_ms

        # 计算当前处于哪个周期段 / Calculate which cycle segment
        cycle_time_elapsed = ((bounties_clone - _CORPUS_TIME_MILLIS) % _FULL_CYCLE + _FULL_CYCLE) % _FULL_CYCLE
        cycle_time_left = _FULL_CYCLE - cycle_time_elapsed
        self.is_corpus: bool = cycle_time_left > _STATE_MAXIMUM

        self.state: str = "Grineer" if self.is_corpus else "Corpus"

        # 时间格式化处理 / Round to minute
        minutes_coef = 1000 * 60
        expiry_ms = round(float(now_ms + millis_left) / minutes_coef) * minutes_coef
        self.expiry: datetime = datetime.fromtimestamp(expiry_ms / 1000, tz=timezone.utc)
        self.activation = datetime.fromtimestamp(
            (expiry_ms - _STATE_MAXIMUM) / 1000, tz=timezone.utc
        )

        self.time_left: str = time_delta_to_string(millis_left)
        self.expired: bool = self.expiry < datetime.now(timezone.utc)
