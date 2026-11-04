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
    gameRef = fields.CharField(max_length=255, null=True, description="Lotus引用")
    bulkTradable = fields.BooleanField(null=True, description="可批量交易")
    maxRank = fields.IntField(null=True, description="最大等级")
    ducats = fields.IntField(null=True, description="杜卡币")
    name = fields.CharField(max_length=255, null=True, db_index=True, description="物品名称")
    icon = fields.CharField(max_length=500, null=True, description="图标")
    thumb = fields.CharField(max_length=500, null=True, description="缩略图")
    vaulted = fields.BooleanField(null=True, description="遗物是否入库")
    maxAmberStars = fields.IntField(null=True, description="阿耶檀识黄星星")
    maxCyanStars = fields.IntField(null=True, description="阿耶檀识蓝星星")
    baseEndo = fields.IntField(null=True, description="基础内融核心")
    reqMasteryRank = fields.IntField(null=True, description="段位等级限制")
    tradingTax = fields.IntField(null=True, description="交易税")

    # ── 以下字段对齐 API 的 Item 模型（data-models 文档）──
    enName = fields.CharField(max_length=255, null=True, description="英文名称")
    tags = fields.JSONField(null=True, description="物品标签（weapon/mod/relic…）")
    setRoot = fields.BooleanField(null=True, description="是否套装根")
    setParts = fields.JSONField(null=True, description="套装成员 ID 列表")
    quantityInSet = fields.IntField(null=True, description="套装内数量")
    rarity = fields.CharField(max_length=50, null=True, description="稀有度")
    subtypes = fields.JSONField(null=True, description="子类型列表")
    maxCharges = fields.IntField(null=True, description="最大充能数")
    endoMultiplier = fields.FloatField(null=True, description="内融核心倍率")
    vosfor = fields.IntField(null=True, description="Vosfor 值")
    tradable = fields.BooleanField(null=True, description="是否可交易")
    subIcon = fields.CharField(max_length=500, null=True, description="子图标")
    description = fields.TextField(null=True, description="物品描述")
    wikiLink = fields.CharField(max_length=500, null=True, description="Wiki 链接")

    class Meta:
        table = "ordersitems"
