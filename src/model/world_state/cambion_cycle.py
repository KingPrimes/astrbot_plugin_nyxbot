"""
CambionCycle Model / 魔胎之境循环模型

对应 Java: CambionCycle.java
依赖 CetusCycle 实例，直接复制其时间，将 白昼→FASS、夜晚→VOME。

不继承 BastWorldState，是纯计算模型。

参考: https://github.com/WFCD/warframe-worldstate-parser
"""
from __future__ import annotations

from datetime import datetime

from .cetus_cycle import CetusCycle


class CambionCycle:
    """魔胎之境循环 / Cambion Drift Cycle

    对应 Java: CambionCycle
    FASS（对应夜灵平原白昼）/ VOME（对应夜灵平原夜晚）。
    直接复制 CetusCycle 的时间数据。
    """

    def __init__(self, cycle: CetusCycle) -> None:
        """
        Args:
            cycle: 已构造好的 CetusCycle 实例
        """
        self.activation: datetime = cycle.activation
        self.expiry: datetime = cycle.expiry
        self.active: str = "FASS" if cycle.is_day else "VOME"
        self.time_left: str = cycle.time_left
