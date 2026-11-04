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
from ..model.market.entities import RivenWeapon
from ..util.i18n_utils import extract_i18n


class RivenService:
    """紫卡分析服务。"""

    # ══════════════════════════════════════════════════════════════════
    # 数据同步（原 data_sources_init.py）
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def _sync_cdn_resource(
        cls,
        fetch_fn,
        model_cls,
        key_field: str,
        build_instance,
        log_name: str,
    ) -> None:
        """通用 CDN 资源同步骨架 — 获取数据 → 空检查 → simple_upsert → 日志。"""
        from .data_sync import DataSyncService

        logger.info(f"从 CdnClient 加载{log_name}数据")
        data = await fetch_fn()
        if not data:
            logger.warning(f"{log_name}数据为空，跳过初始化")
            return

        new_count, _ = await DataSyncService.simple_upsert(
            model_cls=model_cls,
            data=data,
            key_field=key_field,
            build_instance=build_instance,
            prune=True,  # 整份快照：上游删掉的词条本地也要删
        )
        total = await model_cls.all().count()
        logger.info(f"{log_name}数据初始化完成，共 {total} 条记录（本次新增 {new_count} 条）")

    @classmethod
    async def sync_tion_data(cls) -> None:
        """初始化 RivenTion（紫卡词条参数）表数据 — 从 CDN。"""
        await cls._sync_cdn_resource(
            fetch_fn=CdnClient.fetch_riven_tion,
            model_cls=RivenTion,
            key_field="url_name",
            build_instance=lambda item: RivenTion(
                effect=item.get("effect"),
                group=item.get("group"),
                negative_only=bool(item.get("negative_only")),
                positive_is_negative=bool(item.get("positive_is_negative")),
                prefix=item.get("prefix"),
                search_only=bool(item.get("search_only")),
                suffix=item.get("suffix"),
                unit=item.get("unit") or item.get("units"),
                url_name=item.get("url_name", ""),
                exclusive_to=item.get("exclusive_to"),
            ),
            log_name="紫卡词条参数",
        )

    @classmethod
    async def sync_tion_alias_data(cls) -> None:
        """初始化 RivenTionAlias（紫卡词条别名）表数据 — 从 CDN。"""
        await cls._sync_cdn_resource(
            fetch_fn=CdnClient.fetch_riven_tion_alias,
            model_cls=RivenTionAlias,
            key_field="cn",
            build_instance=lambda item: RivenTionAlias(cn=item["cn"], en=item.get("en")),
            log_name="紫卡词条别名",
        )

    @classmethod
    async def sync_analyse_trend_data(cls) -> None:
        """初始化 RivenAnalyseTrend（紫卡分析参数）表数据 — 从 CDN。"""
        await cls._sync_cdn_resource(
            fetch_fn=CdnClient.fetch_riven_analyse_trend,
            model_cls=RivenAnalyseTrend,
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
            log_name="紫卡分析参数",
        )

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

        rows: list[dict] = []
        for raw in data:
            entity = RivenWeapon.model_validate(raw)
            row = {
                "id": entity.id,
                "slug": entity.slug,
                "gameRef": entity.game_ref,
                "group": entity.group,
                "rivenType": entity.riven_type,
                "disposition": entity.disposition,
                "reqMasteryRank": entity.req_mastery_rank,
            }
            row.update(extract_i18n(raw))
            rows.append({k: v for k, v in row.items() if v is not None or k == "id"})

        update_fields = sorted(
            {key for row in rows for key in row} - {"id"}
        )
        total_upserted = await DataSyncService.batch_upsert(
            model_cls=RivenItems,
            items=rows,
            key_field="id",
            build_instance=lambda row: RivenItems(**row),
            update_fields=update_fields,
        )
        total = await RivenItems.all().count()
        logger.info(f"紫卡武器数据初始化完成，共 {total} 条记录（本次处理 {total_upserted} 条）")

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
                "unit": item.unit,
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
