"""
Event Model / 新闻/活动模型

对应 Java: Event.java
继承 BastWorldState，包含 Messages、Prop、Icon、Priority、ImageUrl、Date 等。
"""
from __future__ import annotations

from pydantic import Field

from .base import BastWorldState, DateField
from .message import Message


class Event(BastWorldState):
    """新闻/活动 / News Event

    对应 Java: Event extends BastWorldState
    """

    messages: list[Message] = Field(default_factory=list, alias="Messages")
    prop: str | None = Field(default=None, alias="Prop")
    icon: str | None = Field(default=None, alias="Icon")
    priority: bool | None = Field(default=None, alias="Priority")
    mobile_only: bool | None = Field(default=None, alias="MobileOnly")
    community: bool | None = Field(default=None, alias="Community")
    date: DateField | None = Field(default=None, alias="Date")
    image_url: str | None = Field(default=None, alias="ImageUrl")
    event_start_date: DateField | None = Field(default=None, alias="EventStartDate")
    event_end_date: DateField | None = Field(default=None, alias="EventEndDate")
    hide_end_date_modifier: bool = Field(default=False, alias="HideEndDateModifier")

