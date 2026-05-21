"""
Data Sources Initialization / 数据源初始化

从导出 JSON 文件 + CDN 获取 Warframe 数据并保存到 SQLite 数据库中。

架构说明：
- 解析层（export_parsers.py）：负责读取 JSON → 数据清洗/转换 → 返回 list[dict]
- 持久层（当前文件）：负责 DB 引擎初始化 → 调用解析层获取数据 → 批量 upsert
"""
from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from tortoise import Tortoise
from tortoise.models import Model as TortoiseModel

from astrbot.api import logger

from ..api import CdnClient, MarketClient
from ..config import get_db_debug
from ..model import (
    Alias,
    Ephemeras,
    LichSisterWeapons,
    OrdersItems,
    RivenAnalyseTrend,
    RivenItems,
    RivenTion,
    RivenTionAlias,
)
from ..model.export.night_wave import NightWave
from ..model.export.nodes import Nodes
from ..model.export.reward.reward import Reward
from ..model.export.reward.reward_pool import RewardPool
from ..model.export.weapons import Weapons
from ..model.state_translation import StateTranslation
from ..util import get_public_data_path
from .export_downloader import ExportDir, resolve_export_filename, sever_export_files
from .export_parsers import (
    parse_all_export_translations,
    parse_cdn_translations,
    # Nodes 解析
    parse_export_regions_to_nodes,
    # NightWave 解析
    parse_export_sortie_rewards_to_nightwave,
    # Weapons 解析
    parse_export_weapons_to_weapons,
)

_T = TypeVar("_T", bound=TortoiseModel)

# ============================================================
# 初始化完成信号量（供命令/API 等待初始化完成）
# ============================================================
_init_complete: asyncio.Event = asyncio.Event()


def set_init_complete() -> None:
    """标记初始化完成，唤醒所有等待者。"""
    _init_complete.set()


async def init_ready() -> None:
    """阻塞等待直到数据初始化完成。命令执行前可调用此函数确保数据就绪。"""
    await _init_complete.wait()

# ============================================================
# Tortoise ORM 模型模块路径
#
# AstrBot 以完全限定包名加载插件（如 data.plugins.astrbot_plugin_nyxbot），
# 因此从 __name__ 可以动态推导出完整的模型模块路径。
#
# 示例：
#   __name__ = "data.plugins.astrbot_plugin_nyxbot.src.init.data_sources_init"
#   ↓ rsplit(".", 2)[0] + ".model"
#   = "data.plugins.astrbot_plugin_nyxbot.src.model"
#
# 这样 Tortoise ORM 使用 importlib.import_module() 导入的模块，
# 与插件自身相对导入的模块在 sys.modules 中拥有相同的 key，
# 从而彻底避免"双模块冲突"问题。
# ============================================================
_MODEL_MODULE = __name__.rsplit(".", 2)[0] + ".model"
_MODELS_MODULES = [_MODEL_MODULE]

_tortoise_initialized: bool = False

_BATCH_SIZE = 1000


async def get_engine():
    """初始化 Tortoise ORM 并建表（单例）。"""
    _db_path: str = os.path.join(get_public_data_path(),"nyxbot.db")
    logger.debug(f"数据库路径: {_db_path}")
    global _tortoise_initialized
    if not _tortoise_initialized:
        # 根据配置开关控制 Tortoise ORM 的 SQL 日志输出
        if get_db_debug():
            logging.getLogger("tortoise.db_client").setLevel(logging.DEBUG)
            logging.getLogger("tortoise").setLevel(logging.DEBUG)
            logger.info("数据库调试模式已启用")
        else:
            logging.getLogger("tortoise.db_client").setLevel(logging.INFO)
            logging.getLogger("tortoise").setLevel(logging.INFO)

        db_url = f"sqlite://{_db_path}"
        await Tortoise.init(
            db_url=db_url,
            modules={"models": _MODELS_MODULES},
        )
        await Tortoise.generate_schemas()
        _tortoise_initialized = True
    return Tortoise.get_connection("default")


async def get_session():
    """获取 Tortoise ORM 数据库事务上下文。"""
    await get_engine()
    return Tortoise


async def close_engine() -> None:
    """关闭 TortoiseORM 连接。"""
    global _tortoise_initialized
    if _tortoise_initialized:
        await Tortoise.close_connections()
        _tortoise_initialized = False
        logger.info("TortoiseORM connections closed")


# ======================================================================
# 数据初始化函数（upsert 模式：对比插入，不删除已有数据）
# ======================================================================


async def init_alias_data() -> None:
    """从 CDN 获取别名数据，对比插入新的记录（优化版：一次查询 + 批量插入）。"""
    logger.info("从 CdnClient 加载别名数据")
    data = await CdnClient.fetch_alias()
    if not data:
        logger.warning("别名数据为空，跳过初始化")
        return
    await get_engine()

    # 一次查询获取所有已存在的 cn
    existing_cns: set[str] = {
        row.cn async for row in Alias.filter(
            cn__in=[item["cn"] for item in data]
        ).only("cn")
    }

    # 过滤出新记录
    new_items: list[Alias] = []
    for item in data:
        if item["cn"] not in existing_cns:
            new_items.append(Alias(cn=item["cn"], en=item["en"]))

    new_count = 0
    if new_items:
        created = await Alias.bulk_create(new_items)
        new_count = len(created) if created else 0

    total = await Alias.all().count()
    logger.info(f"别名数据初始化完成，共 {total} 条记录（本次新增 {new_count} 条）")


async def init_riven_tion_data() -> None:
    """初始化 RivenTion（紫卡词条参数）表数据 — 从 CDN。"""
    logger.info("从 CdnClient 加载紫卡词条参数数据")
    data = await CdnClient.fetch_rive_tion()
    if not data:
        logger.warning("紫卡词条参数数据为空，跳过初始化")
        return
    await get_engine()

    # 按 url_name 去重
    url_names = [item.get("url_name", "") for item in data if item.get("url_name")]
    existing_url_names: set[str] = {
        row.url_name async for row in RivenTion.filter(
            url_name__in=url_names
        ).only("url_name")
    }

    new_items: list[RivenTion] = []
    for item in data:
        url_name = item.get("url_name", "")
        if url_name and url_name not in existing_url_names:
            new_items.append(RivenTion(
                effect=item.get("effect"),
                group=item.get("group"),
                negative_only=item.get("negative_only"),
                positive_is_negative=item.get("positive_is_negative"),
                prefix=item.get("prefix"),
                search_only=item.get("search_only"),
                suffix=item.get("suffix"),
                units=item.get("units"),
                url_name=url_name,
                exclusive_to=item.get("exclusive_to"),
            ))

    new_count = 0
    if new_items:
        created = await RivenTion.bulk_create(new_items)
        new_count = len(created) if created else 0

    total = await RivenTion.all().count()
    logger.info(f"紫卡词条参数数据初始化完成，共 {total} 条记录（本次新增 {new_count} 条）")


async def init_riven_tion_alias_data() -> None:
    """初始化 RivenTionAlias（紫卡词条别名）表数据 — 从 CDN。"""
    logger.info("从 CdnClient 加载紫卡词条别名数据")
    data = await CdnClient.fetch_riven_tion_alias()
    if not data:
        logger.warning("紫卡词条别名数据为空，跳过初始化")
        return
    await get_engine()

    # 按 cn 去重（与 alias 初始化逻辑一致）
    existing_cns: set[str] = {
        row.cn async for row in RivenTionAlias.filter(
            cn__in=[item["cn"] for item in data]
        ).only("cn")
    }

    new_items: list[RivenTionAlias] = []
    for item in data:
        if item["cn"] not in existing_cns:
            new_items.append(RivenTionAlias(cn=item["cn"], en=item.get("en")))

    new_count = 0
    if new_items:
        created = await RivenTionAlias.bulk_create(new_items)
        new_count = len(created) if created else 0

    total = await RivenTionAlias.all().count()
    logger.info(f"紫卡词条别名数据初始化完成，共 {total} 条记录（本次新增 {new_count} 条）")


async def init_riven_analyse_trend_data() -> None:
    """初始化 RivenAnalyseTrend（紫卡分析参数）表数据 — 从 CDN。"""
    logger.info("从 CdnClient 加载紫卡分析参数数据")
    data = await CdnClient.fetch_riven_analyse_trend()
    if not data:
        logger.warning("紫卡分析参数数据为空，跳过初始化")
        return
    await get_engine()

    # 按 name 去重
    existing_names: set[str] = {
        row.name async for row in RivenAnalyseTrend.filter(
            name__in=[item["name"] for item in data]
        ).only("name")
    }

    new_items: list[RivenAnalyseTrend] = []
    for item in data:
        if item["name"] not in existing_names:
            new_items.append(RivenAnalyseTrend(
                archwing=item.get("archwing"),
                melle=item.get("melle"),
                name=item["name"],
                pistol=item.get("pistol"),
                prefix=item.get("prefix"),
                rifle=item.get("rifle"),
                shotgun=item.get("shotgun"),
                suffix=item.get("suffix"),
            ))

    new_count = 0
    if new_items:
        created = await RivenAnalyseTrend.bulk_create(new_items)
        new_count = len(created) if created else 0

    total = await RivenAnalyseTrend.all().count()
    logger.info(f"紫卡分析参数数据初始化完成，共 {total} 条记录（本次新增 {new_count} 条）")


async def init_riven_items_data() -> None:
    """初始化 RivenItems（紫卡物品）表数据 — 从 Market API。"""
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
        items.append({**item, **_extract_i18n(item)})

    total_upserted = await _batch_upsert_riven_items(items)
    total = await RivenItems.all().count()
    logger.info(f"紫卡武器数据初始化完成，共 {total} 条记录（本次处理 {total_upserted} 条）")


async def init_orders_items_data() -> None:
    """初始化 OrdersItems（市场订单物品）表数据 — 从 Market API。

    从 /items 端点获取所有可交易物品列表，提取基础字段并通过
    _batch_upsert_orders_items() 进行对比插入。
    注意：ducats/vaulted/tradingTax 等字段在 /items 端点中不可用。
    """
    logger.info("从 Market API 加载物品数据...")
    await get_engine()

    resp = await MarketClient.fetch_items()
    if not resp:
        logger.warning("物品数据为空，跳过初始化")
        return

    data: list[dict] = resp.get("data", [])
    if not data:
        logger.warning("物品数据为空，跳过")
        return

    items: list[dict] = []
    for item in data:
        items.append({**item, **_extract_i18n(item)})

    total_upserted = await _batch_upsert_orders_items(items)
    total = await OrdersItems.all().count()
    logger.info(f"物品数据初始化完成，共 {total} 条记录（本次处理 {total_upserted} 条）")


async def init_ephemeras_data() -> None:
    """初始化 Ephemeras（幻纹）表数据 — 从 Market API。

    从 /lich/ephemeras 和 /sister/ephemeras 两个端点获取数据，
    合并后通过 _batch_upsert_ephemeras() 统一 upsert。
    """
    logger.info("从 Market API 加载幻纹数据...")
    await get_engine()

    all_data: list[dict] = []

    # 赤毒幻纹
    lich_resp = await MarketClient.fetch_lich_ephemeras()
    if lich_resp:
        lich_data = lich_resp.get("data", [])
        for item in lich_data:
            all_data.append({**item, **_extract_i18n(item)})
        logger.info(f"赤毒幻纹: {len(lich_data)} 条")
    else:
        logger.warning("赤毒幻纹数据为空")

    # 信条幻纹
    sister_resp = await MarketClient.fetch_sister_ephemeras()
    if sister_resp:
        sister_data = sister_resp.get("data", [])
        for item in sister_data:
            all_data.append({**item, **_extract_i18n(item)})
        logger.info(f"信条幻纹: {len(sister_data)} 条")
    else:
        logger.warning("信条幻纹数据为空")

    if not all_data:
        logger.warning("无幻纹数据可插入")
        return

    total_upserted = await _batch_upsert_ephemeras(all_data)
    total = await Ephemeras.all().count()
    logger.info(f"幻纹数据初始化完成，共 {total} 条记录（本次处理 {total_upserted} 条）")


async def init_lich_sister_weapons_data() -> None:
    """初始化 LichSisterWeapons（信条/赤毒武器）表数据 — 从 Market API。

    从 /lich/weapons 和 /sister/weapons 两个端点获取数据，
    合并后通过 _batch_upsert_lich_sister_weapons() 统一 upsert。
    """
    logger.info("从 Market API 加载信条/赤毒武器数据...")
    await get_engine()

    all_data: list[dict] = []

    # 赤毒武器
    lich_resp = await MarketClient.fetch_lich_weapons()
    if lich_resp:
        lich_data = lich_resp.get("data", [])
        for item in lich_data:
            all_data.append({**item, **_extract_i18n(item)})
        logger.info(f"赤毒武器: {len(lich_data)} 条")
    else:
        logger.warning("赤毒武器数据为空")

    # 信条武器
    sister_resp = await MarketClient.fetch_sister_weapons()
    if sister_resp:
        sister_data = sister_resp.get("data", [])
        for item in sister_data:
            all_data.append({**item, **_extract_i18n(item)})
        logger.info(f"信条武器: {len(sister_data)} 条")
    else:
        logger.warning("信条武器数据为空")

    if not all_data:
        logger.warning("无信条/赤毒武器数据可插入")
        return

    total_upserted = await _batch_upsert_lich_sister_weapons(all_data)
    total = await LichSisterWeapons.all().count()
    logger.info(f"信条/赤毒武器数据初始化完成，共 {total} 条记录（本次处理 {total_upserted} 条）")


async def init_night_wave_data() -> None:
    """初始化 NightWave（电波任务）表数据 — 从导出文件。

    镜像 Java initNightWave() (WarframeDataSource.java:395-414):
    解析 ExportSortieRewards_zh.json → ExportNightwave.challenges
    → 批量 upsert 到 NightWave 表
    """
    await get_engine()

    if not await sever_export_files():
        return

    filename = await resolve_export_filename("ExportSortieRewards")
    if not filename:
        logger.warning("未找到 ExportSortieRewards 导出文件，跳过电波任务数据初始化")
        return

    export_path = Path(ExportDir) / filename
    if not export_path.exists():
        logger.warning(f"{filename} 不存在，跳过电波任务数据初始化")
        return

    logger.info(f"从 {filename} 解析电波任务数据...")
    items = parse_export_sortie_rewards_to_nightwave(str(export_path))
    if not items:
        logger.warning("电波任务数据为空，跳过")
        return

    logger.info(f"已解析 {filename}: {len(items)} 条")
    total_upserted = await _batch_upsert_night_wave(items)
    total = await NightWave.all().count()
    logger.info(f"电波任务数据初始化完成，共 {total} 条记录（本次处理 {total_upserted} 条）")


async def init_relics_data() -> None:
    """初始化 Relics（遗物）表数据（含关联的 RelicRewards）。"""
    logger.info("初始化遗物数据 (stub) — 待实现")


async def init_sentinels_data() -> None:
    """初始化 Sentinels（守护/宠物）表数据。"""
    logger.info("初始化守护/宠物数据 (stub) — 待实现")


async def init_upgrades_data() -> None:
    """初始化 Upgrades（MOD/升级组件）表数据。"""
    logger.info("初始化MOD/升级组件数据 (stub) — 待实现")


async def init_warframes_data() -> None:
    """初始化 Warframes（战甲）表数据（含关联的 WarframeAbility）。"""
    logger.info("初始化战甲数据 (stub) — 待实现")


async def init_reward_pool_data() -> None:
    """初始化 RewardPool（奖励池）表数据 — 从 CDN，含嵌套 Rewards。"""
    logger.info("从 CdnClient 加载奖励池数据")
    data = await CdnClient.fetch_reward_pool()
    if not data:
        logger.warning("奖励池数据为空，跳过初始化")
        return
    await get_engine()

    # Phase 1: 按 uniqueName 去重，插入 RewardPool
    existing_pools: set[str] = {
        row.uniqueName async for row in RewardPool.filter(
            uniqueName__in=[item["uniqueName"] for item in data]
        ).only("uniqueName")
    }

    new_pools: list[RewardPool] = []
    for item in data:
        if item["uniqueName"] not in existing_pools:
            new_pools.append(RewardPool(uniqueName=item["uniqueName"]))

    new_pool_count = 0
    if new_pools:
        created = await RewardPool.bulk_create(new_pools)
        new_pool_count = len(created) if created else 0

    # Phase 2: 处理嵌套的 rewards 子表
    all_rewards_data: list[dict] = []
    for item in data:
        rewards = item.get("rewards", [])
        for r in rewards:
            r["_pool_uniqueName"] = item["uniqueName"]
        all_rewards_data.extend(rewards)

    new_reward_count = 0
    if all_rewards_data:
        reward_ids = [r["id"] for r in all_rewards_data if r.get("id")]
        existing_reward_ids: set[str] = {
            row.id async for row in Reward.filter(
                id__in=reward_ids
            ).only("id")
        }

        new_rewards: list[Reward] = []
        for r in all_rewards_data:
            rid = r.get("id")
            if rid and rid not in existing_reward_ids:
                new_rewards.append(Reward(
                    id=rid,
                    item=r.get("item", ""),
                    rarity=r.get("rarity"),
                    itemCount=r.get("itemCount"),
                    reward_pool_id=r.get("_pool_uniqueName"),
                ))

        if new_rewards:
            created_r = await Reward.bulk_create(new_rewards)
            new_reward_count = len(created_r) if created_r else 0

    total_pools = await RewardPool.all().count()
    total_rewards = await Reward.all().count()
    logger.info(
        f"奖励池数据初始化完成，共 {total_pools} 个奖励池（本次新增 {new_pool_count} 个），"
        f"共 {total_rewards} 条奖励记录（本次新增 {new_reward_count} 条）"
    )


# ======================================================================
# 通用批量 Upsert（模块内部私有）
#
# 优化策略：
# - Phase A: bulk_create(ignore_conflicts=True) 批量插入新记录
# - Phase B: 一次 SELECT 找到所有已存在的记录 → 脏检测 (dirty checking)
#   仅当字段值实际变化时才加入更新列表 → 分批 bulk_update() 批量写回
#   将 O(N) 次 SQL 往返降到 O(1) 次查询 + O(N/batch_size) 次更新，
#   且避免数据未变化时的冗余 UPDATE。
# ======================================================================


async def _generic_batch_upsert(
    model_cls: type[_T],
    items: list[dict],
    key_field: str,
    build_instance: Callable[[dict], _T],
    update_fields: list[str],
    batch_size: int = _BATCH_SIZE,
) -> int:
    """通用分批 Upsert（Phase A + Phase B 脏检测）。

    Args:
        model_cls: TortoiseORM 模型类。
        items: 待 upsert 的数据字典列表。
        key_field: 唯一键字段名（如 "uniqueName" 或 "id"）。
        build_instance: 从 dict 构建模型实例的工厂函数。
        update_fields: Phase B 需要比较并更新的字段列表。
        batch_size: 批处理大小，默认 _BATCH_SIZE。

    Returns:
        本次处理的记录总数（Phase A 新增 + Phase B 实际变更数）。
    """
    total_upserted = 0

    # --- Phase A: bulk_create(ignore_conflicts=True) 批量插入新记录 ---
    batch: list[_T] = []
    for item in items:
        batch.append(build_instance(item))
        if len(batch) >= batch_size:
            created = await model_cls.bulk_create(batch, ignore_conflicts=True)
            if created:
                total_upserted += len(created)
            batch.clear()
    if batch:
        created = await model_cls.bulk_create(batch, ignore_conflicts=True)
        if created:
            total_upserted += len(created)

    # --- Phase B: 脏检测 + 分批 bulk_update ---
    keys = [item[key_field] for item in items]
    existing_map = {
        getattr(obj, key_field): obj
        async for obj in model_cls.filter(**{f"{key_field}__in": keys})
    }

    to_update: list[_T] = []
    for item in items:
        obj = existing_map.get(item[key_field])
        if obj is not None:
            # 构建新实例用于值比较
            new_instance = build_instance(item)
            changed = False
            for field in update_fields:
                old_val = getattr(obj, field)
                new_val = getattr(new_instance, field)
                if old_val != new_val:
                    setattr(obj, field, new_val)
                    changed = True
            if changed:
                to_update.append(obj)
                if len(to_update) >= batch_size:
                    await model_cls.bulk_update(to_update, fields=update_fields)
                    total_upserted += len(to_update)
                    to_update.clear()
    if to_update:
        await model_cls.bulk_update(to_update, fields=update_fields)
        total_upserted += len(to_update)

    return total_upserted


# ======================================================================
# 各模型的批量 Upsert 函数（thin wrappers，调用 _generic_batch_upsert）
# ======================================================================


async def _batch_upsert_translations(items: list[dict]) -> int:
    """分批 upsert StateTranslation（含脏检测）。"""
    return await _generic_batch_upsert(
        model_cls=StateTranslation,
        items=items,
        key_field="uniqueName",
        build_instance=lambda item: StateTranslation(
            uniqueName=item["uniqueName"],
            name=item.get("name", ""),
            description=str(item.get("description", "")) if item.get("description") is not None else "",
            type=item.get("type", ""),
            parentName=item.get("parentName"),
        ),
        update_fields=["name", "description", "type", "parentName"],
    )


async def _batch_upsert_nodes(items: list[dict]) -> int:
    """分批 upsert Nodes（含脏检测）。"""
    node_fields = [f for f in items[0].keys() if f != "uniqueName"] if items else []
    return await _generic_batch_upsert(
        model_cls=Nodes,
        items=items,
        key_field="uniqueName",
        build_instance=lambda item: Nodes(**item),
        update_fields=node_fields,
    )


async def _batch_upsert_weapons(items: list[dict]) -> int:
    """分批 upsert Weapons（含脏检测）。"""
    weapon_fields = [f for f in items[0].keys() if f != "uniqueName"] if items else []
    return await _generic_batch_upsert(
        model_cls=Weapons,
        items=items,
        key_field="uniqueName",
        build_instance=lambda item: Weapons(**item),
        update_fields=weapon_fields,
    )


async def _batch_upsert_night_wave(items: list[dict]) -> int:
    """分批 upsert NightWave（含脏检测）。"""
    nw_fields = [f for f in items[0].keys() if f != "uniqueName"] if items else []
    return await _generic_batch_upsert(
        model_cls=NightWave,
        items=items,
        key_field="uniqueName",
        build_instance=lambda item: NightWave(**item),
        update_fields=nw_fields,
    )


# ======================================================================
# 辅助函数：从 API item 中提取 i18n 本地化字段
# ======================================================================


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


# ======================================================================
# 批量 Upsert 函数 — OrdersItems / Ephemeras / LichSisterWeapons / RivenItems
# ======================================================================


async def _batch_upsert_orders_items(items: list[dict]) -> int:
    """分批 upsert OrdersItems（含脏检测）。"""
    return await _generic_batch_upsert(
        model_cls=OrdersItems,
        items=items,
        key_field="id",
        build_instance=lambda item: OrdersItems(
            id=item["id"],
            slug=item.get("slug"),
            gameRef=item.get("gameRef"),
            maxRank=item.get("maxRank"),
            name=item.get("name"),
            icon=item.get("icon"),
            thumb=item.get("thumb"),
            bulkTradable=item.get("bulkTradable"),
            ducats=item.get("ducats"),
            vaulted=item.get("vaulted"),
            maxAmberStars=item.get("maxAmberStars"),
            maxCyanStars=item.get("maxCyanStars"),
            baseEndo=item.get("baseEndo"),
        ),
        update_fields=[
            "slug", "gameRef", "maxRank", "name", "icon",
            "thumb", "bulkTradable", "ducats", "vaulted",
            "maxAmberStars", "maxCyanStars", "baseEndo",
        ],
    )


async def _batch_upsert_ephemeras(items: list[dict]) -> int:
    """分批 upsert Ephemeras（含脏检测）。"""
    return await _generic_batch_upsert(
        model_cls=Ephemeras,
        items=items,
        key_field="id",
        build_instance=lambda item: Ephemeras(
            id=item["id"],
            slug=item.get("slug"),
            gameRef=item.get("gameRef"),
            animation=item.get("animation"),
            element=item.get("element"),
            name=item.get("name"),
            icon=item.get("icon"),
            thumb=item.get("thumb"),
        ),
        update_fields=["slug", "gameRef", "animation", "element", "name", "icon", "thumb"],
    )


async def _batch_upsert_lich_sister_weapons(items: list[dict]) -> int:
    """分批 upsert LichSisterWeapons（含脏检测）。"""
    return await _generic_batch_upsert(
        model_cls=LichSisterWeapons,
        items=items,
        key_field="id",
        build_instance=lambda item: LichSisterWeapons(
            id=item["id"],
            slug=item.get("slug"),
            icon=item.get("icon"),
            gameRef=item.get("gameRef"),
            reqMasteryRank=item.get("reqMasteryRank"),
            name=item.get("name"),
            thumb=item.get("thumb"),
        ),
        update_fields=["slug", "icon", "gameRef", "reqMasteryRank", "name", "thumb"],
    )


async def _batch_upsert_riven_items(items: list[dict]) -> int:
    """分批 upsert RivenItems（含脏检测）。"""
    return await _generic_batch_upsert(
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


# ======================================================================
# 编排函数（薄包装：调解析 → 调 upsert → 日志）
# ======================================================================


async def init_state_translation_data() -> bool:
    """初始化 StateTranslation（状态翻译）表数据。

    镜像 Java initStateTranslation() (WarframeDataSource.java:364-393):
    Phase 1: 遍历 Export*.json 导出文件 → parse_all_export_translations()
    Phase 2: 从 CDN 获取自定义数据 → parse_cdn_translations()
    统一 _batch_upsert_translations()

    Returns:
        True 表示初始化成功完成；False 表示导出文件下载失败（应跳过后续初始化）。
    """
    logger.info("开始初始化状态翻译数据...")
    await get_engine()

    if not await sever_export_files():
        logger.warning("导出文件下载失败，跳过所有数据初始化")
        return False

    # Phase 1: 从导出文件解析
    all_items = await parse_all_export_translations()

    # Phase 2: 从 CDN 获取自定义数据
    cdn_items = await parse_cdn_translations()
    all_items.extend(cdn_items)

    if not all_items:
        logger.warning("无状态翻译数据可插入")
        return True

    total_upserted = await _batch_upsert_translations(all_items)
    total = await StateTranslation.all().count()
    logger.info(f"状态翻译数据初始化完成，共 {total} 条记录（本次处理 {total_upserted} 条）")
    return True


async def init_nodes_data() -> None:
    """初始化星图节点数据 — 从导出文件 + CDN。

    镜像 Java initNodes() (WarframeDataSource.java:416-426):
    Phase 1: 解析 ExportRegions_zh.json → Nodes dicts
    Phase 2: 从 CDN 获取自定义 Nodes 数据
    统一 _batch_upsert_nodes()
    """
    await get_engine()

    all_items: list[dict] = []

    # Phase 1: 从导出文件解析
    filename = await resolve_export_filename("ExportRegions")
    if filename:
        export_path = Path(ExportDir) / filename
        if export_path.exists():
            logger.info(f"从 {filename} 解析星图节点数据...")
            items = parse_export_regions_to_nodes(str(export_path))
            all_items.extend(items)
            logger.info(f"已解析 {filename}: {len(items)} 条")
        else:
            logger.warning(f"{filename} 不存在，跳过导出文件解析")
    else:
        logger.warning("未找到 ExportRegions 导出文件，跳过导出文件解析")

    # Phase 2: 从 CDN 获取自定义 Nodes 数据
    logger.info("从 CDN 获取自定义星图节点数据...")
    cdn_data = await CdnClient.fetch_nodes()
    if cdn_data:
        all_items.extend(cdn_data)
        logger.info(f"CDN 节点数据: {len(cdn_data)} 条")
    else:
        logger.warning("CDN 星图节点数据为空，跳过")

    if not all_items:
        logger.warning("无星图节点数据可插入")
        return

    total_upserted = await _batch_upsert_nodes(all_items)
    total = await Nodes.all().count()
    logger.info(f"星图节点数据初始化完成，共 {total} 条记录（本次处理 {total_upserted} 条）")


async def init_weapons_data() -> None:
    """初始化武器数据 — 从导出文件。

    镜像 Java initWeapons() (WarframeDataSource.java:436-442):
    Phase 1: 解析 ExportWeapons_zh.json → Weapons dicts
    （含 damagePerShot 序列化 + englishName 提取）
    统一 _batch_upsert_weapons()
    """
    await get_engine()

    if not await sever_export_files():
        return

    filename = await resolve_export_filename("ExportWeapons")
    if not filename:
        logger.warning("未找到 ExportWeapons 导出文件，跳过武器数据初始化")
        return

    export_path = Path(ExportDir) / filename
    if not export_path.exists():
        logger.warning(f"{filename} 不存在，跳过武器数据初始化")
        return

    logger.info(f"从 {filename} 解析武器数据...")
    items = parse_export_weapons_to_weapons(str(export_path))
    if not items:
        logger.warning("武器数据为空，跳过")
        return

    logger.info(f"已解析 {filename}: {len(items)} 条")
    total_upserted = await _batch_upsert_weapons(items)
    total = await Weapons.all().count()
    logger.info(f"武器数据初始化完成，共 {total} 条记录（本次处理 {total_upserted} 条）")
