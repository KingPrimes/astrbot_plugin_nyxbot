"""Arbitration models / 仲裁模型

对齐 Go: ``internal/warframe/arbitration.go`` 的 ``Arbitration`` 条目与
``internal/draw/draw_arbitration.go`` 的绘图输入。

- ``Arbitration``：只承载 arbys.txt 的两列与推导出的到期时间，不落库。
- ``ArbitrationView``：查询层补齐节点名/任务类型/派系/评级后的绘图 DTO。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..util.time_utils import time_delta_to_string
from ..wenum.faction import FactionEnum


@dataclass(frozen=True, slots=True)
class Arbitration:
    """单条仲裁 / One arbitration entry.

    对齐 Go ``Arbitration``：只保存数据源的两列与到期时间；节点名、任务类型、
    派系、评级一律在查询/绘图转换时补齐，避免解析早于 nodes 导入时固化错误值。
    """

    activation: int
    """开始时间（Unix 秒，arbys.txt 第一列）。"""
    node_key: str
    """节点 SolNode ID（arbys.txt 第二列）。"""
    expiry: int
    """结束时间（Unix 秒，= activation + 3600）。"""

    @property
    def activation_dt(self) -> datetime:
        """开始时间（本地时区 datetime）。"""
        return datetime.fromtimestamp(self.activation)

    @property
    def expiry_dt(self) -> datetime:
        """结束时间（本地时区 datetime）。"""
        return datetime.fromtimestamp(self.expiry)


@dataclass(frozen=True, slots=True)
class ArbitrationView:
    """仲裁绘图输入 / Arbitration draw DTO.

    对齐 Go ``draw.Arbitration``：节点显示名、任务类型中文名、派系枚举、评级
    均由 ``ArbitrationService`` 在查询时补齐，卡片只负责渲染。
    """

    activation: datetime
    expiry: datetime
    node: str
    mission_name: str
    faction: FactionEnum
    tier: str

    @property
    def time_left(self) -> str:
        """剩余时间文本（与 Go timeDeltaToString 一致）。"""
        delta_ms = int((self.expiry - datetime.now()).total_seconds() * 1000)
        return time_delta_to_string(delta_ms)

    @property
    def activation_str(self) -> str:
        """开始时间文本（本地时区）。"""
        return self.activation.strftime("%Y-%m-%d %H:%M:%S")
