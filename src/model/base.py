"""Shared Pydantic base model with populate_by_name=True.

所有需要别名反序列化的 Pydantic 模型统一继承此类，
消除各子模块中重复的 model_config 声明。
"""
from __future__ import annotations

from pydantic import BaseModel


class BaseModelWithAlias(BaseModel):
    """带别名序列化的基类，统一配置 populate_by_name=True。"""

    model_config = {"populate_by_name": True}
