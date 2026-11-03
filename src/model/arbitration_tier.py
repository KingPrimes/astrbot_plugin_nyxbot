"""Arbitration tier model / 仲裁节点分级模型

对齐 Go: ``internal/model/warframe/arbitration_tier.go``（表 ``arbitration_tier``）。
数据源为 CDN 的 ``warframe/arbitration_tiers.json``。
"""
from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class ArbitrationTier(Model):
    """仲裁节点分级 / Arbitration node tier.

    ``key`` 为节点 SolNode ID，与 ``nodes.uniqueName`` 同键；
    ``tier`` 取 S/A/B/C/D/F，未收录节点由消费侧按 F 处理。
    """

    key = fields.CharField(
        max_length=255,
        pk=True,
        description="节点 SolNode ID",
    )
    tier = fields.CharField(
        max_length=1,
        description="评级 S/A/B/C/D/F",
    )

    class Meta:
        table = "arbitration_tier"
