"""Riven service / 紫卡分析服务

提供紫卡趋势分析和属性计算功能，以及本地紫卡相关数据查询和数据同步。
"""
from __future__ import annotations

from tortoise.exceptions import DoesNotExist
from tortoise.expressions import Q

from astrbot.api import logger

from ..api import CdnClient, MarketClient
from ..model.riven_analyse_trend import RivenAnalyseTrend
from ..model.riven_items import RivenItems
from ..model.riven_tion import RivenTion
from ..model.riven_tion_alias import RivenTionAlias


class RivenService:
    """紫卡分析服务。"""

    # ══════════════════════════════════════════════════════════════════
    # 数据同步（原 data_sources_init.py）
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def sync_tion_data(cls) -> None:
        """初始化 RivenTion（紫卡词条参数）表数据 — 从 CDN。"""
        from .data_sync import DataSyncService

        logger.info("从 CdnClient 加载紫卡词条参数数据")
        data = await CdnClient.fetch_rive_tion()
        if not data:
            logger.warning("紫卡词条参数数据为空，跳过初始化")
            return

        new_count, _ = await DataSyncService.simple_upsert(
            model_cls=RivenTion,
            data=data,
            key_field="url_name",
            build_instance=lambda item: RivenTion(
                effect=item.get("effect"),
                group=item.get("group"),
                negative_only=item.get("negative_only"),
                positive_is_negative=item.get("positive_is_negative"),
                prefix=item.get("prefix"),
                search_only=item.get("search_only"),
                suffix=item.get("suffix"),
                units=item.get("units"),
                url_name=item.get("url_name", ""),
                exclusive_to=item.get("exclusive_to"),
            ),
        )
        total = await RivenTion.all().count()
        logger.info(f"紫卡词条参数数据初始化完成，共 {total} 条记录（本次新增 {new_count} 条）")

    @classmethod
    async def sync_tion_alias_data(cls) -> None:
        """初始化 RivenTionAlias（紫卡词条别名）表数据 — 从 CDN。"""
        from .data_sync import DataSyncService

        logger.info("从 CdnClient 加载紫卡词条别名数据")
        data = await CdnClient.fetch_riven_tion_alias()
        if not data:
            logger.warning("紫卡词条别名数据为空，跳过初始化")
            return

        new_count, _ = await DataSyncService.simple_upsert(
            model_cls=RivenTionAlias,
            data=data,
            key_field="cn",
            build_instance=lambda item: RivenTionAlias(cn=item["cn"], en=item.get("en")),
        )
        total = await RivenTionAlias.all().count()
        logger.info(f"紫卡词条别名数据初始化完成，共 {total} 条记录（本次新增 {new_count} 条）")

    @classmethod
    async def sync_analyse_trend_data(cls) -> None:
        """初始化 RivenAnalyseTrend（紫卡分析参数）表数据 — 从 CDN。"""
        from .data_sync import DataSyncService

        logger.info("从 CdnClient 加载紫卡分析参数数据")
        data = await CdnClient.fetch_riven_analyse_trend()
        if not data:
            logger.warning("紫卡分析参数数据为空，跳过初始化")
            return

        new_count, _ = await DataSyncService.simple_upsert(
            model_cls=RivenAnalyseTrend,
            data=data,
            key_field="name",
            build_instance=lambda item: RivenAnalyseTrend(
                archwing=item.get("archwing"),
                melle=item.get("melle"),
                name=item["name"],
                pistol=item.get("pistol"),
                prefix=item.get("prefix"),
                rifle=item.get("rifle"),
                shotgun=item.get("shotgun"),
                suffix=item.get("suffix"),
            ),
        )
        total = await RivenAnalyseTrend.all().count()
        logger.info(f"紫卡分析参数数据初始化完成，共 {total} 条记录（本次新增 {new_count} 条）")

    @classmethod
    async def sync_items_data(cls) -> None:
        """初始化 RivenItems（紫卡物品）表数据 — 从 Market API。"""
        from ..init.engine import get_engine
        from .data_sync import DataSyncService

        logger.info("从 Market API 加载紫卡武器数据...")
        await get_engine()

        resp = await MarketClient.fetch_riven_weapons()
        if not resp:
            logger.warning("紫卡武器数据为空，跳过初始化")
            return

        data: list[dict] = resp.get("data", [])
        if not data:
            logger.warning("紫卡武器数据为空，跳过")
            return

        items: list[dict] = []
        for item in data:
            items.append({**item, **cls._extract_i18n(item)})

        total_upserted = await DataSyncService.batch_upsert(
            model_cls=RivenItems,
            items=items,
            key_field="id",
            build_instance=lambda item: RivenItems(
                id=item["id"],
                slug=item.get("slug"),
                gameRef=item.get("gameRef"),
                group=item.get("group"),
                rivenType=item.get("rivenType"),
                disposition=item.get("disposition"),
                reqMasteryRank=item.get("reqMasteryRank"),
                name=item.get("name"),
                icon=item.get("icon"),
                thumb=item.get("thumb"),
            ),
            update_fields=[
                "slug", "gameRef", "group", "rivenType",
                "disposition", "reqMasteryRank", "name", "icon", "thumb",
            ],
        )
        total = await RivenItems.all().count()
        logger.info(f"紫卡武器数据初始化完成，共 {total} 条记录（本次处理 {total_upserted} 条）")

    @staticmethod
    def _extract_i18n(item: dict, lang: str = "zh-hans") -> dict:
        """从 API 返回的 item 中提取 i18n 本地化 name/icon/thumb。

        所有 Market API 端点返回的 item 都遵循统一结构:
            item["i18n"][lang] = {"name": "...", "icon": "...", "thumb": "..."}

        Args:
            item: API 返回的原始 item 字典。
            lang: 目标语言代码，默认 "zh-hans"。

        Returns:
            包含 name/icon/thumb 的 dict，缺失时值为 None。
        """
        i18n = item.get("i18n", {})
        localized = i18n.get(lang, {})
        return {
            "name": localized.get("name"),
            "icon": localized.get("icon"),
            "thumb": localized.get("thumb"),
        }

    # ══════════════════════════════════════════════════════════════════
    # 远程 API（原有，保持不变）
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def get_weapon_list(cls) -> list[dict] | None:
        """获取紫卡武器列表（远程）。"""
        ...  # TODO: 由 API 层实现

    @classmethod
    async def search_auctions(
        cls,
        weapon_url_name: str,
        sort_by: str = "price_asc",
        page: int = 0,
    ) -> dict | None:
        """搜索紫卡拍卖。

        Args:
            weapon_url_name: 武器 url_name。
            sort_by: 排序方式。
            page: 页码。

        Returns:
            拍卖搜索结果。
        """
        ...  # TODO: 由 API 层实现

    # ══════════════════════════════════════════════════════════════════
    # 本地数据库查询（原有，保持不变）
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def get_riven_item(cls, slug: str) -> dict | None:
        """从本地 RivenItems 表查询紫卡物品信息。

        Args:
            slug: URL slug。

        Returns:
            紫卡物品信息。
        """
        try:
            item = await RivenItems.get(slug=slug)
            return {
                "id": item.id,
                "slug": item.slug,
                "gameRef": item.gameRef,
                "group": item.group,
                "rivenType": item.rivenType,
                "disposition": item.disposition,
                "reqMasteryRank": item.reqMasteryRank,
                "name": item.name,
                "icon": item.icon,
                "thumb": item.thumb,
            }
        except DoesNotExist:
            return None

    @classmethod
    async def get_analysis_params(cls, name: str) -> dict | None:
        """从本地 RivenAnalyseTrend 表查询分析参数。

        Args:
            name: 效果名称。

        Returns:
            分析参数字典。
        """
        try:
            item = await RivenAnalyseTrend.get(name=name)
            return {
                "archwing": item.archwing,
                "melle": item.melle,
                "name": item.name,
                "pistol": item.pistol,
                "prefix": item.prefix,
                "rifle": item.rifle,
                "shotgun": item.shotgun,
                "suffix": item.suffix,
            }
        except DoesNotExist:
            return None

    @classmethod
    async def get_tion_params(cls, effect: str) -> dict | None:
        """从本地 RivenTion 表查询词条参数。

        Args:
            effect: 词条效果名称。

        Returns:
            词条参数字典。
        """
        try:
            item = await RivenTion.get(effect=effect)
            return {
                "effect": item.effect,
                "group": item.group,
                "negative_only": item.negative_only,
                "positive_is_negative": item.positive_is_negative,
                "prefix": item.prefix,
                "search_only": item.search_only,
                "suffix": item.suffix,
                "units": item.units,
                "url_name": item.url_name,
                "exclusive_to": item.exclusive_to,
            }
        except DoesNotExist:
            return None

    @classmethod
    async def search_tion_alias(
        cls, keyword: str, page: int = 1, page_size: int = 20
    ):
        """从本地 RivenTionAlias 表模糊搜索词条别名。

        Returns:
            (记录列表, 总数) 的元组。
        """
        offset = (page - 1) * page_size
        qs = RivenTionAlias.filter(
            Q(en__contains=keyword) | Q(cn__contains=keyword)
        )
        total = await qs.count()
        items = await qs.offset(offset).limit(page_size)
        return list(items), total
