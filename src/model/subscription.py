"""Subscription Model / 订阅模型"""
from __future__ import annotations

from typing import Optional
from sqlmodel import SQLModel, Field


class MissionSubscribe(SQLModel, table=True):
    """任务订阅配置"""
    __table_args__ = {'extend_existing': True}

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, description="用户 ID")
    group_id: str = Field(index=True, description="群组 ID")
    mission_type: str = Field(description="订阅任务类型: alerts, fissures, invasions, sortie, arbitrations, void")
    enabled: bool = Field(default=True, description="是否启用")


class MissionSubscribeUser(SQLModel, table=True):
    """用户订阅配置（扩展）"""
    __table_args__ = {'extend_existing': True}

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, description="用户 ID")
    subscribe_type: str = Field(description="订阅类型")
    subscribe_target: str = Field(description="订阅目标")
    enabled: bool = Field(default=True, description="是否启用")
