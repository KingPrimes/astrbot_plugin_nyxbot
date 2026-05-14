"""
Data Sources Initialization / 数据源初始化
从 CDN 获取 Warframe 数据并保存到 SQLite 数据库中。
"""
from __future__ import annotations

import logging

from tortoise import Tortoise
from astrbot.api import logger

from ..api import DataSourceClient
from ..config import get_db_debug
from ..model import Alias
from ..model.exprot.nodes import ExprotNodes as Nodes
from ..util import _get_db_path

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


async def get_engine():
    """初始化 Tortoise ORM 并建表（单例）。"""
    _db_path: str = _get_db_path() + "\\nyxbot.db"
    print(_db_path)
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
    """从 CDN 获取别名数据，对比插入新的记录（不做全量删除）。"""
    logger.info("从 DataSourceClient 加载别名数据")
    data = await DataSourceClient.fetch_alias()
    if not data:
        logger.warning("别名数据为空，跳过初始化")
        return
    await get_engine()
    new_count = 0
    for item in data:
        _, created = await Alias.get_or_create(cn=item["cn"], defaults={"en": item["en"]})
        if created:
            new_count += 1
    total = await Alias.all().count()
    logger.info(f"别名数据初始化完成，共 {total} 条记录（本次新增 {new_count} 条）")


async def init_nodes_data() -> None:
    """从 CDN 获取星图节点数据，对比插入新的记录（不做全量删除）。"""
    logger.info("从 DataSourceClient 加载星图节点数据")
    data = await DataSourceClient.fetch_nodes()
    if not data:
        logger.warning("星图节点数据为空，跳过初始化")
        return
    await get_engine()
    new_count = 0
    for item in data:
        _, created = await Nodes.get_or_create(uniqueName=item["uniqueName"], defaults=item)
        if created:
            new_count += 1
    count = await Nodes.all().count()
    logger.info(f"星图节点数据初始化完成，共 {count} 条记录（本次新增 {new_count} 条）")


async def init_riven_tion_data() -> None:
    """初始化 RivenTion（紫卡词条参数）表数据。"""
    logger.info("初始化紫卡词条参数数据 (stub)")
    await get_engine()


async def init_riven_tion_alias_data() -> None:
    """初始化 RivenTionAlias（紫卡词条别名）表数据。"""
    logger.info("初始化紫卡词条别名数据 (stub)")
    await get_engine()


async def init_riven_analyse_trend_data() -> None:
    """初始化 RivenAnalyseTrend（紫卡分析参数）表数据。"""
    logger.info("初始化紫卡分析参数数据 (stub)")
    await get_engine()


async def init_riven_items_data() -> None:
    """初始化 RivenItems（紫卡物品）表数据。"""
    logger.info("初始化紫卡物品数据 (stub)")
    await get_engine()


async def init_orders_items_data() -> None:
    """初始化 OrdersItems（市场订单物品）表数据。"""
    logger.info("初始化市场订单物品数据 (stub)")
    await get_engine()


async def init_ephemeras_data() -> None:
    """初始化 Ephemeras（幻纹）表数据。"""
    logger.info("初始化幻纹数据 (stub)")
    await get_engine()


async def init_lich_sister_weapons_data() -> None:
    """初始化 LichSisterWeapons（信条/赤毒武器）表数据。"""
    logger.info("初始化信条/赤毒武器数据 (stub)")
    await get_engine()


async def init_state_translation_data() -> None:
    """初始化 StateTranslation（状态翻译）表数据。"""
    logger.info("初始化状态翻译数据 (stub)")
    await get_engine()


async def init_customs_data() -> None:
    """初始化 Customs（外观）表数据。"""
    logger.info("初始化外观数据 (stub)")
    await get_engine()


async def init_mod_set_data() -> None:
    """初始化 ModSet（MOD 套装）表数据。"""
    logger.info("初始化MOD套装数据 (stub)")
    await get_engine()


async def init_night_wave_data() -> None:
    """初始化 NightWave（电波任务）表数据。"""
    logger.info("初始化电波任务数据 (stub)")
    await get_engine()


async def init_relics_data() -> None:
    """初始化 Relics（遗物）表数据（含关联的 RelicRewards）。"""
    logger.info("初始化遗物数据 (stub)")
    await get_engine()


async def init_sentinels_data() -> None:
    """初始化 Sentinels（守护/宠物）表数据。"""
    logger.info("初始化守护/宠物数据 (stub)")
    await get_engine()


async def init_upgrades_data() -> None:
    """初始化 Upgrades（MOD/升级组件）表数据。"""
    logger.info("初始化MOD/升级组件数据 (stub)")
    await get_engine()


async def init_warframes_data() -> None:
    """初始化 Warframes（战甲）表数据（含关联的 WarframeAbility）。"""
    logger.info("初始化战甲数据 (stub)")
    await get_engine()


async def init_weapons_data() -> None:
    """初始化 Weapons（武器）表数据。"""
    logger.info("初始化武器数据 (stub)")
    await get_engine()


async def init_reward_data() -> None:
    """初始化 Reward（具体奖励）表数据。"""
    logger.info("初始化奖励数据 (stub)")
    await get_engine()


async def init_reward_pool_data() -> None:
    """初始化 RewardPool（奖励池）表数据（含关联的 Reward）。"""
    logger.info("初始化奖励池数据 (stub)")
    await get_engine()
