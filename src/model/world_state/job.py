"""
Job Model / 集团赏金任务详情模型

对应 Java: Job.java
不继承 BastWorldState，包含任务类型、描述、奖励池、段位限制、敌人等级等。
"""
from __future__ import annotations

from pydantic import Field

from .base import BaseModelWithAlias


class Job(BaseModelWithAlias):
    """集团赏金任务详情 / Syndicate Bounty Job

    对应 Java: Job
    用于 SyndicateMission.jobs 列表。
    """

    type: str | None = Field(default=None, alias="jobType")
    desc: str | None = Field(default=None, alias="desc")
    rewards: str | None = Field(default=None, alias="rewards")
    reward_pool: dict | None = Field(default=None, alias="rewardPool")  # RewardPool 引用，暂用 dict
    mastery_req: int | None = Field(default=None, alias="masteryReq")
    min_level: int | None = Field(default=None, alias="minEnemyLevel")
    max_level: int | None = Field(default=None, alias="maxEnemyLevel")
    xp_amounts: list[int] = Field(default_factory=list, alias="xpAmounts")
    endless: bool | None = Field(default=None, alias="endless")
    location_tag: str | None = Field(default=None, alias="locationTag")
    is_vault: bool | None = Field(default=None, alias="isVault")

