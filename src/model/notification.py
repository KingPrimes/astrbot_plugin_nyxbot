"""Notification Model / 通知历史模型"""
from __future__ import annotations

from typing import Optional
from sqlmodel import SQLModel, Field


class NotificationHistory(SQLModel, table=True):
    """通知历史记录"""
    __table_args__ = {'extend_existing': True}

    id: Optional[int] = Field(default=None, primary_key=True)
    mission_type: str = Field(index=True, description="任务类型")
    mission_id: str = Field(index=True, description="任务唯一 ID")
    title: str = Field(default="", description="通知标题")
    content: str = Field(default="", description="通知内容")
    notified_at: str = Field(description="通知时间（ISO 8601）")
    notified_users: str = Field(default="", description="已通知的用户列表（逗号分隔）")
