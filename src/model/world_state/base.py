"""
Base Models for WorldState / 世界状态基础模型
包含 BaseModelWithAlias（别名序列化基类）、BastWorldState 基类、
DateField（MongoDB 时间戳包装）、Id（MongoDB OID 包装）。

对应 Java:
- BastWorldState.java — 基类 (_id + Activation + Expiry + time_left 计算属性)
- DateField.java — {"$date": {"$numberLong": "..."}} 包装
- BastWorldState.Id — {"$oid": "..."} 包装
"""
from __future__ import annotations

import time

from pydantic import Field

from ...util.time_utils import time_delta_to_string
from ..base import BaseModelWithAlias


class Id(BaseModelWithAlias):
    """MongoDB OID 包装 / MongoDB OID Wrapper

    JSON 格式: {"$oid": "507f1f77bcf86cd799439011"}
    """

    oid: str = Field(alias="$oid")


class DateField(BaseModelWithAlias):
    """MongoDB 日期包装 / MongoDB Date Wrapper

    JSON 格式: {"$date": {"$numberLong": "1734567890123"}}
    其中 $numberLong 的值可能是 int 或 str 类型。
    """

    class DateValue(BaseModelWithAlias):
        """内部日期数据 / Inner date data"""
        number_long: int | str = Field(alias="$numberLong")

        def to_millis(self) -> int:
            """转换为毫秒时间戳 / Convert to milliseconds timestamp"""
            return int(self.number_long)

    date: DateValue = Field(alias="$date")

    @property
    def time_millis(self) -> int:
        """获取毫秒时间戳 / Get timestamp in milliseconds"""
        return self.date.to_millis()

    def time_left(self) -> str:
        """计算剩余时间 / Calculate time left

        Returns:
            可读的剩余时间字符串，格式与 Java TimeUtils.timeDeltaToString 一致。
            Readable time left string, same format as Java TimeUtils.timeDeltaToString.
        """
        if self.date is None:
            return "未知"
        delta_ms = self.time_millis - int(time.time() * 1000)
        return time_delta_to_string(delta_ms)


class BastWorldState(BaseModelWithAlias):
    """世界状态基类 / World State Base Class

    所有从 API JSON 反序列化的世界状态模型（Alert、Sortie 等）继承此类。
    提供 _id、Activation、Expiry 三个公共字段 + time_left 计算属性。

    对应 Java: BastWorldState.java
    """

    id: Id | None = Field(default=None, alias="_id")
    activation: DateField | None = Field(default=None, alias="Activation")
    expiry: DateField | None = Field(default=None, alias="Expiry")

    @property
    def time_left(self) -> str:
        """剩余时间 / Time left

        Returns:
            可读的剩余时间字符串 / Readable time left string
        """
        if self.expiry is None:
            return "未知"
        return self.expiry.time_left()
