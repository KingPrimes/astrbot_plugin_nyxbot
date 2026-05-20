"""
OrdersItems Model / 市场订单物品模型

对应 Java: OrdersItems.java
"""
from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class OrdersItems(Model):
    """Warframe Orders Items 数据"""

    id = fields.CharField(max_length=255, pk=True, description="唯一字符串ID")
    slug = fields.CharField(max_length=50, null=True, description="URL路径名称")
    gameRef = fields.CharField(max_length=255, null=True, source_field="game_ref", description="Lotus引用")
    bulkTradable = fields.BooleanField(null=True, source_field="bulk_tradable", description="可批量交易")
    maxRank = fields.IntField(null=True, source_field="max_rank", description="最大等级")
    ducats = fields.IntField(null=True, description="杜卡币")
    name = fields.CharField(max_length=255, null=True, description="物品名称")
    icon = fields.CharField(max_length=500, null=True, description="图标")
    thumb = fields.CharField(max_length=500, null=True, description="缩略图")
    vaulted = fields.BooleanField(null=True, description="遗物是否入库")
    maxAmberStars = fields.IntField(null=True, source_field="max_amber_stars", description="阿耶檀识黄星星")
    maxCyanStars = fields.IntField(null=True, source_field="max_cyan_stars", description="阿耶檀识蓝星星")
    baseEndo = fields.IntField(null=True, source_field="base_endo", description="基础内融核心")
    reqMasteryRank = fields.IntField(null=True, source_field="req_mastery_rank", description="段位等级限制")
    tradingTax = fields.IntField(null=True, source_field="trading_tax", description="交易税")

    class Meta:
        table = "ordersitems"
