"""
Data Sources Initialization / 数据源初始化
从 CDN 获取 Warframe 数据并保存到 SQLite 数据库中。
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

from tortoise import Tortoise
from astrbot.api import logger

from ..api import DataSourceClient
from ..api.data_source import ExportDir, ExportHash
from ..config import get_db_debug
from ..model import Alias
from ..model.export.nodes import ExprotNodes as Nodes
from ..model.state_translation import StateTranslation
from ..util import get_public_data_path
from ..wenum.state_type import StateTypeEnum

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
    _db_path: str = os.path.join(get_public_data_path(),"nyxbot.db")
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


# ======================================================================
# StateTranslation 初始化辅助
# ======================================================================

_ST_FILE_CONFIG: dict[str, dict[str, object]] = {
    "ExportCustoms":       {"json_key": "ExportCustoms",       "default_type": StateTypeEnum.ALL},
    "ExportDrones":        {"json_key": "ExportDrones",        "default_type": StateTypeEnum.ALL},
    "ExportFlavour":       {"json_key": "ExportFlavour",       "default_type": StateTypeEnum.ALL},
    "ExportGear":          {"json_key": "ExportGear",          "default_type": StateTypeEnum.GEAR},
    "ExportKeys":          {"json_key": "ExportKeys",          "default_type": StateTypeEnum.KEYS},
    "ExportRelicArcane":   {"json_key": "ExportRelicArcane",   "default_type": StateTypeEnum.ALL},
    "ExportResources":     {"json_key": "ExportResources",     "default_type": StateTypeEnum.RESOURCES},
    "ExportSentinels":     {"json_key": "ExportSentinels",     "default_type": StateTypeEnum.SENTINELS},
    "ExportSortieRewards": {"json_key": "ExportOther",         "default_type": StateTypeEnum.OTHER},  # 特例
    "ExportUpgrades":      {"json_key": "ExportUpgrades",      "default_type": StateTypeEnum.MODS},
    "ExportWarframes":     {"json_key": "ExportWarframes",     "default_type": StateTypeEnum.WARFRAMES},
    "ExportWeapons":       {"json_key": "ExportWeapons",       "default_type": StateTypeEnum.WEAPONS},
}

_BATCH_SIZE = 500


def _resolve_state_type(unique_name: str, default_type: StateTypeEnum) -> str:
    """根据 uniqueName 正则匹配 StateTypeEnum，返回枚举的成员名。

    镜像 Java 端逻辑 (WarframeDataSource.java:289-290, 383-388):

    1. 遍历 StateTypeEnum 所有枚举值
    2. 如果枚举的 key (正则) 非空 → re.fullmatch(key, unique_name)
    3. 匹配成功则返回该枚举的 .name（如 "RELIC_BRONZE"）
    4. 全部不匹配 → 返回 default_type.name

    Java 的 String.matches() 等价于 Python 的 re.fullmatch()。
    """
    for enum_val in StateTypeEnum:
        if enum_val.key:  # 空 KEY 跳过（空正则会匹配空字符串，不会误匹配）
            if re.fullmatch(enum_val.key, unique_name):
                return enum_val.name
    return default_type.name


async def _parse_export_to_translations(
    export_path: str,
    json_key: str,
    default_type: StateTypeEnum,
) -> list[dict]:
    """解析单个 DE 导出 JSON 文件，返回带 type 字段的 dict 列表。

    镜像 Java parsingExportJsonToStateTranslation() (WarframeDataSource.java:274):
    1. 读取 JSON 文件
    2. 提取 json_key 对应的数组
    3. 过滤 name 为空的项
    4. 对每项调用 _resolve_state_type 进行 type 正则匹配
    5. 处理 description 字段（支持 list/str，镜像 Java setDescription()）
    """
    result: list[dict] = []
    raw = json.loads(Path(export_path).read_text(encoding="utf-8"))
    items = raw.get(json_key, [])
    if not isinstance(items, list):
        return result

    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not name:
            continue

        unique_name = item.get("uniqueName", "")
        item["type"] = _resolve_state_type(unique_name, default_type)

        # 处理 description 字段（镜像 Java StateTranslation.setDescription()）
        desc = item.get("description")
        if isinstance(desc, list):
            item["description"] = str(desc[0]) if desc else ""
        elif desc is not None:
            item["description"] = str(desc)
        else:
            item["description"] = ""

        # 确保 parentName 字段存在
        if "parentName" not in item:
            item["parentName"] = None

        result.append(item)

    return result


async def _batch_upsert_translations(items: list[dict]) -> int:
    """分批 upsert StateTranslation，覆盖更新已有记录所有字段。

    两步走策略（镜像 Java saveAll 覆盖语义）:
    Phase A - bulk_create(ignore_conflicts=True): 快速批量插入新记录（占大多数）
    Phase B - update_or_create: 逐条覆盖更新已存在记录的所有字段

    Args:
        items: 已处理好的 dict 列表

    Returns:
        int: 插入 + 更新的记录总数
    """
    total_upserted = 0

    # Phase A: 批量插入新记录（首次运行时大部分是新数据，性能最优）
    batch: list[StateTranslation] = []
    for item in items:
        batch.append(StateTranslation(
            uniqueName=item["uniqueName"],
            name=item.get("name", ""),
            description=str(item.get("description", "")) if item.get("description") is not None else "",
            type=item.get("type", ""),
            parentName=item.get("parentName"),
        ))
        if len(batch) >= _BATCH_SIZE:
            created = await StateTranslation.bulk_create(batch, ignore_conflicts=True)
            if created:
                total_upserted += len(created)
            batch.clear()
    if batch:
        created = await StateTranslation.bulk_create(batch, ignore_conflicts=True)
        if created:
            total_upserted += len(created)

    # Phase B: 覆盖更新已存在的记录
    for item in items:
        _, created = await StateTranslation.update_or_create(
            uniqueName=item["uniqueName"],
            defaults={
                "name": item.get("name", ""),
                "description": str(item.get("description", "")) if item.get("description") is not None else "",
                "type": item.get("type", ""),
                "parentName": item.get("parentName"),
            },
        )
        if not created:
            total_upserted += 1

    return total_upserted


async def init_state_translation_data() -> None:
    """初始化 StateTranslation（状态翻译）表数据。"""
    logger.info("开始初始化状态翻译数据...")
    await get_engine()

    all_items: list[dict] = []

    # ========== Phase 1: 从 Hash.json 动态获取导出文件列表 ==========
    hash_path = Path(ExportHash)
    if hash_path.exists():
        hash_data = json.loads(hash_path.read_text(encoding="utf-8"))
        for filename in hash_data:
            if not filename.endswith("_zh.json"):
                continue
            base_name = filename[:-len("_zh.json")]
            config = _ST_FILE_CONFIG.get(base_name)
            if config is None:
                continue
            export_path = Path(ExportDir) / filename
            if not export_path.exists():
                logger.warning(f"导出文件不存在，跳过: {export_path}")
                continue
            default_type = config["default_type"]
            assert isinstance(default_type, StateTypeEnum)
            items = await _parse_export_to_translations(
                str(export_path), str(config["json_key"]), default_type
            )
            all_items.extend(items)
            logger.info(f"已解析 {filename}: {len(items)} 条")
    else:
        logger.warning("Hash.json 不存在，跳过导出文件解析阶段")

    # ========== Phase 2: 从 CDN 获取自定义 state_translation 数据 ==========
    logger.info("从 CDN 获取自定义状态翻译数据...")
    data = await DataSourceClient.fetch_state_translations()
    if data:
        for item in data:
            unique_name = item.get("uniqueName", "")
            if not unique_name:
                continue
            item["type"] = _resolve_state_type(unique_name, StateTypeEnum.RESOURCES)
            desc = item.get("description")
            if isinstance(desc, list):
                item["description"] = str(desc[0]) if desc else ""
            elif desc is not None:
                item["description"] = str(desc)
            # 确保 parentName 字段存在
            if "parentName" not in item:
                item["parentName"] = None
        all_items.extend(data)
        logger.info(f"CDN 数据: {len(data)} 条")
    else:
        logger.warning("CDN 状态翻译数据为空，跳过")

    # ========== 统一两步走 upsert ==========
    if not all_items:
        logger.warning("无状态翻译数据可插入")
        return

    total_upserted = await _batch_upsert_translations(all_items)
    total = await StateTranslation.all().count()
    logger.info(f"状态翻译数据初始化完成，共 {total} 条记录（本次处理 {total_upserted} 条）")


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
