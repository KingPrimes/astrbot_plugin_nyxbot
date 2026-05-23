"""
SteelPathOffering Model / 钢铁之路奖励轮换模型

对应 Java: SteelPathOffering.java
不继承 BastWorldState，是基于数学推算的计算模型。
包含 8 个轮换奖励 + 19 个常驻奖励（硬编码数据）。

参考: https://github.com/WFCD/warframe-worldstate-parser
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import NamedTuple

from ...util.time_utils import time_delta_to_string

# 钢铁之路起始日期: 2020-11-16 00:00:00 UTC / Steel Path start date
_START_TIMESTAMP: int = 1605484800

# 轮换奖励 / Rotation rewards (name, cost)
_ROTATION: list[tuple[str, int]] = [
    ("Umbra Forma 蓝图", 150),
    ("50,000 赤毒", 55),
    ("组合枪裂罅 Mod", 75),
    ("3x Forma", 75),
    ("Zaw 裂罅 Mod", 75),
    ("30,000 内融核心", 150),
    ("步枪裂罅 Mod", 75),
    ("霰弹枪裂罅 Mod", 75),
]

# 常驻奖励 / Evergreen rewards (name, cost)
_EVERGREENS: list[tuple[str, int]] = [
    ("裂罅破解器", 20),
    ("军神护肩 蓝图", 15),
    ("军神胸甲 蓝图", 25),
    ("军神头盔 蓝图", 20),
    ("军神护胫 蓝图", 25),
    ("10,000 赤毒", 15),
    ("主要武器赋能槽连接器", 15),
    ("次要武器赋能槽连接器", 15),
    ("遗物组合包", 15),
    ("架式 Forma 蓝图", 10),
    ("三轨幻纹", 3),
    ("颅骨幻纹", 85),
    ("制衡", 35),
    ("Teshin 摇头娃娃", 35),
    ("Gauss 战斗姿态浮印", 15),
    ("Grendel 战斗姿态浮印", 15),
    ("Protea 战斗姿态浮印", 15),
    ("Orokin 茶具", 15),
    ("Xaku 战斗姿态浮印", 15),
]


class SteelPathReward(NamedTuple):
    """钢铁之路奖励 / Steel Path Reward

    对应 Java: SteelPathOffering.SteelPathReward (record)
    """
    name: str
    cost: int

    def __str__(self) -> str:
        return f"{self.name} ({self.cost})"


class SteelPathOffering:
    """钢铁之路奖励轮换 / Steel Path Offering

    对应 Java: SteelPathOffering
    8 周周期（每 7 天轮换一次奖励）。
    """

    def __init__(self) -> None:
        # 计算当前周期索引 / Calculate current rotation index
        now_seconds = int(time.time())
        eight_weeks = 4838400  # 8 周的秒数
        seven_days = 604800    # 7 天的秒数

        seconds_since_start = now_seconds - _START_TIMESTAMP
        ind = (seconds_since_start % eight_weeks) // seven_days

        self.current_reward: SteelPathReward | None = None
        self.next_reward: SteelPathReward | None = None
        if _ROTATION:
            self.current_reward = SteelPathReward(*_ROTATION[ind % len(_ROTATION)])
            self.next_reward = SteelPathReward(*_ROTATION[(ind + 1) % len(_ROTATION)])

        # 计算本周起止时间 / Calculate current week start/end
        now_dt = datetime.now(timezone.utc)
        weekday = now_dt.weekday()  # Monday=0
        # 本周一 00:00:00 UTC (ISO week)
        start_of_week = now_dt.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=weekday)
        end_of_week = start_of_week + timedelta(days=7)

        self.activation: datetime = start_of_week
        self.expiry: datetime = end_of_week
        self.remaining: str = time_delta_to_string(
            int((end_of_week - now_dt).total_seconds() * 1000)
        )

    @property
    def evergreens(self) -> list[SteelPathReward]:
        """常驻奖励池 / Evergreen reward pool"""
        return [SteelPathReward(*e) for e in _EVERGREENS]

    @property
    def rotation(self) -> list[SteelPathReward]:
        """轮换奖励池 / Rotation reward pool"""
        return [SteelPathReward(*r) for r in _ROTATION]
