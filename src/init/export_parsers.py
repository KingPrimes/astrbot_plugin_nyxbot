"""
Export JSON Parsers / 导出 JSON 文件解析器

提供从 Warframe 公共导出 JSON 文件中解析数据的纯函数。
各函数以"接收文件路径 → 返回 list[dict]"模式工作，
与 data_sources_init.py 中的 DB 持久化逻辑完全分离。

镜像 Java: WarframeDataSource.java parsingExportJson*() 系列方法。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from astrbot.api import logger

from ..api import CdnClient
from ..util import to_title_case
from ..wenum.state_type import StateTypeEnum

# ======================================================================
# StateTranslation 文件配置
# 映射: 导出文件名基 -> (json_key, 默认 StateType)
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


# ======================================================================
# 通用辅助
# ======================================================================


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
        if enum_val.key:
            if re.fullmatch(enum_val.key, unique_name):
                return enum_val.name
    return default_type.name


def extract_weapon_english_name(item: dict) -> str:
    """从武器 JSON dict 中提取 englishName。

    镜像 Java Weapons.contEnglishName() (Weapons.java:139-154):
    1. 从 description 中提取 （英文：...） 子串
    2. 调用 to_title_case() 转换（等价 Java StringUtils.convertToCamelCase）
    3. 处理 MK1- 前缀特殊逻辑

    Args:
        item: 武器 JSON dict，必须含 description 和 name 字段

    Returns:
        str: 提取的英文名称，无法提取时返回空字符串。
    """
    desc = item.get("description")
    if not desc or not isinstance(desc, str) or not desc.strip():
        return ""

    m = re.search(r"（英文：(.+?)）", desc)
    if not m:
        return ""

    e_name = to_title_case(m.group(1))
    name = item.get("name", "")

    # 处理 MK1- 前缀（Java Weapons.contEnglishName() L145-149）
    if name and name.upper() == "MK1-":
        if e_name and e_name != desc and e_name.upper() != "MK1-":
            return f"Mk1-{e_name}"

    # 如果提取到的英文名与 description 相同，说明提取失败（Java L150-152）
    if e_name and e_name == desc:
        return ""

    return e_name


# ======================================================================
# StateTranslation 解析
# ======================================================================


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
    4. 对每项调用 resolve_state_type 进行 type 正则匹配
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


async def parse_all_export_translations() -> list[dict]:
    """遍历 _ST_FILE_CONFIG 配置的导出文件，批量解析 StateTranslation。

    镜像 Java initStateTranslation() Phase 1 (WarframeDataSource.java:364-378):
    遍历 ExportCustoms / ExportDrones / ... / ExportWeapons 等文件，
    逐个解析后聚合返回。

    通过 resolve_export_filename() 从 Hash.json 动态解析实际文件名，
    避免硬编码语言后缀（如 _zh.json），从而支持任意语言。

    依赖 export_downloader.ExportHash 和 ExportDir，由调用方确保
    sever_export_files() 已执行完毕。

    Returns:
        list[dict]: 所有导出文件解析后的 state_translation dict 列表。
    """
    from .export_downloader import ExportDir, resolve_export_filename

    all_items: list[dict] = []

    for base_name, config in _ST_FILE_CONFIG.items():
        filename = await resolve_export_filename(base_name)
        if not filename:
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

    return all_items


async def parse_cdn_translations() -> list[dict]:
    """从 CDN 获取自定义 StateTranslation 数据并处理。

    镜像 Java initStateTranslation() Phase 2 (WarframeDataSource.java:381-392):
    从 StateTranslationService（CDN 端）获取自定义翻译数据，
    对每项执行 type 正则匹配和 description 处理。

    Returns:
        list[dict]: 处理后的 state_translation dict 列表。
    """
    data = await CdnClient.fetch_state_translations()
    if not data:
        logger.warning("CDN 状态翻译数据为空，跳过")
        return []

    result: list[dict] = []
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
        else:
            item["description"] = ""
        # 确保 parentName 字段存在
        if "parentName" not in item:
            item["parentName"] = None
        result.append(item)

    logger.info(f"CDN 状态翻译数据: {len(result)} 条")
    return result


# ======================================================================
# Nodes 解析
# ======================================================================


def parse_export_regions_to_nodes(export_path: str) -> list[dict]:
    """解析 ExportRegions_zh.json，返回 Nodes 兼容的 dict 列表。

    镜像 Java parsingExportJson("ExportRegions_zh.json", "ExportRegions", Nodes.class)
    (WarframeDataSource.java:418):

    字段直通映射（Java Nodes.java ↔ Python Nodes 字段完全一致）:
    - uniqueName / name / systemName / systemIndex / nodeType
    - masteryReq / missionIndex / factionIndex / minEnemyLevel / maxEnemyLevel

    Args:
        export_path: ExportRegions_zh.json 的完整路径

    Returns:
        list[dict]: 过滤空 name 后的节点数据列表
    """
    result: list[dict] = []
    raw = json.loads(Path(export_path).read_text(encoding="utf-8"))
    items = raw.get("ExportRegions", [])
    if not isinstance(items, list):
        return result

    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not name:
            continue
        result.append(item)

    return result


# ======================================================================
# Weapons 解析
# ======================================================================


def parse_export_weapons_to_weapons(export_path: str) -> list[dict]:
    """解析 ExportWeapons_zh.json，返回 Weapons 兼容的 dict 列表。

    镜像 Java parsingExportJson("ExportWeapons_zh.json", "ExportWeapons", Weapons.class)
    + forEach contEnglishName() (WarframeDataSource.java:438-439):

    特殊处理:
    1. damagePerShot: Java 是 List<Double> / Python 模型是 TextField
       → 需 json.dumps() 序列化为 JSON 字符串
    2. englishName: 从 description 中提取 （英文：...）→ to_title_case() 转换
       → 调用 extract_weapon_english_name()

    Args:
        export_path: ExportWeapons_zh.json 的完整路径

    Returns:
        list[dict]: 处理后的武器数据列表
    """
    result: list[dict] = []
    raw = json.loads(Path(export_path).read_text(encoding="utf-8"))
    items = raw.get("ExportWeapons", [])
    if not isinstance(items, list):
        return result

    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not name:
            continue

        # --- 特殊处理 1: damagePerShot 序列化 ---
        dps = item.get("damagePerShot")
        if dps is not None and isinstance(dps, list):
            item["damagePerShot"] = json.dumps(dps)

        # --- 特殊处理 2: englishName 提取 ---
        # Java: weapons.forEach(w -> w.setEnglishName(w.contEnglishName()));
        item["englishName"] = extract_weapon_english_name(item)

        result.append(item)

    return result


# ======================================================================
# NightWave 解析
# ======================================================================


def parse_export_sortie_rewards_to_nightwave(export_path: str) -> list[dict]:
    """解析 ExportSortieRewards_zh.json 中的 NightWave 挑战数据。

    镜像 Java initNightWave() (WarframeDataSource.java:398-404):
    rootNode.get("ExportNightwave").get("challenges") → List<NightWave>

    注意：此文件也包含 Sortie 奖励数据（ExportOther），但我们只取
    ExportNightwave.challenges 分支。

    Args:
        export_path: ExportSortieRewards_zh.json 的完整路径

    Returns:
        list[dict]: 电波挑战数据列表
    """
    result: list[dict] = []
    raw = json.loads(Path(export_path).read_text(encoding="utf-8"))
    export_nightwave = raw.get("ExportNightwave")
    if not isinstance(export_nightwave, dict):
        return result
    challenges = export_nightwave.get("challenges")
    if not isinstance(challenges, list):
        return result

    for item in challenges:
        if not isinstance(item, dict):
            continue
        # uniqueName 是必填字段（Java @NotEmpty / @Id）
        unique_name = item.get("uniqueName")
        if not unique_name:
            continue
        result.append(item)

    return result
