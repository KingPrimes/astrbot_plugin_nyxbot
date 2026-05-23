"""
LibraryInfo Model / 图书馆信息模型

对应 Java: LibraryInfo.java
不继承 BastWorldState，仅含 LastCompletedTargetType 字段。
"""
from __future__ import annotations

from pydantic import Field

from .base import BaseModelWithAlias


class LibraryInfo(BaseModelWithAlias):
    """图书馆信息 / Library Info

    对应 Java: LibraryInfo
    """

    last_completed_target_type: str | None = Field(default=None, alias="LastCompletedTargetType")

