"""Arbitration model / 仲裁预测数据模型

对应 Java: io.github.kingprimes.model.Arbitration

"""
from __future__ import annotations

import time as _time
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from ..wenum.faction import FactionEnum


class Arbitration(BaseModel):
    """仲裁预测任务 — 镜像 Java Arbitration.java

    字段对应第三方仲裁 API 返回的 JSON 结构。
    时间字段为 epoch 秒（float），与 DateField（MongoDB 格式）不同。
    """

    model_config = {"populate_by_name": True}

    activation: float | None = Field(default=None, alias="activation")
    """开始时间 (epoch 秒)"""
    expiry: float | None = Field(default=None, alias="expiry")
    """结束时间 (epoch 秒)"""
    id: str = Field(default="", alias="id")
    """任务代号"""
    node: str = Field(default="", alias="node")
    """节点名称（含行星）"""
    planet: str = Field(default="", alias="planet")
    """行星"""
    enemy: str = Field(default="", alias="enemy")
    """敌人/派系（原始字符串）"""
    type: str = Field(default="", alias="missionType")
    """任务类型（中文）"""
    etc: str = Field(default="", alias="etc")

    # --- 计算属性（镜像 Java getter 方法）---

    @property
    def faction(self) -> FactionEnum:
        """解析派系枚举 — 镜像 Java getEnemy()"""
        enemy_upper = self.enemy.upper() if self.enemy else ""
        for f in FactionEnum:
            if f.name.upper().replace("FC_", "") in enemy_upper:
                return f
        return FactionEnum.FC_NONE

    @property
    def is_worth(self) -> bool:
        """判断是否值得参与 — 镜像 Java isWorth()"""
        is_type = "拦截" in self.type or "防御" in self.type
        is_node = "谷神星" in self.node or "水星" in self.node
        is_enemy = "Grin" in self.enemy or "Infest" in self.enemy
        return is_type and is_node and is_enemy

    @property
    def time_left(self) -> str:
        """剩余时间 — 镜像 Java getTimeLeft()"""
        if self.expiry is None:
            return "未知"
        delta = int(self.expiry - _time.time())
        if delta <= 0:
            return "已过期"
        h, remainder = divmod(delta, 3600)
        m, s = divmod(remainder, 60)
        if h > 0:
            return f"{h}时{m}分"
        return f"{m}分"

    @property
    def activation_str(self) -> str:
        """格式化的开始时间"""
        if self.activation is None:
            return "未知"
        dt = datetime.fromtimestamp(self.activation, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def expiry_str(self) -> str:
        """格式化的结束时间"""
        if self.expiry is None:
            return "未知"
        dt = datetime.fromtimestamp(self.expiry, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
