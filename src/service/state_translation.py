"""StateTranslation service / 状态翻译服务

提供 Warframe 状态翻译查询（基于 StateTranslation 表）。
包含 StateTranslation 的完整数据管道：解析 + 持久化。
"""
from __future__ import annotations

import re
from pathlib import Path

import orjson
from tortoise.exceptions import DoesNotExist
from tortoise.expressions import Q

from astrbot.api import logger

from ..api import CdnClient
from ..model.state_translation import StateTranslation
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


class StateTranslationService:
    """状态翻译服务：StateTranslation 解析 + 同步 + 查询。"""

    # ══════════════════════════════════════════════════════════════════
    # 私有：StateTranslation 解析（原 export_parsers.py）
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
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
            if enum_val.key and re.fullmatch(enum_val.key, unique_name):
                    return enum_val.name
        return default_type.name

    @classmethod
    async def _parse_export_to_translations(
        cls,
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
        raw = orjson.loads(Path(export_path).read_bytes())
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
            item["type"] = cls._resolve_state_type(unique_name, default_type)

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

    @classmethod
    async def _parse_all_export_translations(cls) -> list[dict]:
        """遍历 _ST_FILE_CONFIG 配置的导出文件，批量解析 StateTranslation。

        镜像 Java initStateTranslation() Phase 1 (WarframeDataSource.java:364-378):
        遍历 ExportCustoms / ExportDrones / ... / ExportWeapons 等文件，
        逐个解析后聚合返回。
        """
        from ..init.export_downloader import ExportDir, resolve_export_filename

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
            items = await cls._parse_export_to_translations(
                str(export_path), str(config["json_key"]), default_type
            )
            all_items.extend(items)
            logger.info(f"已解析 {filename}: {len(items)} 条")

        return all_items

    @classmethod
    async def _parse_cdn_translations(cls) -> list[dict]:
        """从 CDN 获取自定义 StateTranslation 数据并处理。

        镜像 Java initStateTranslation() Phase 2 (WarframeDataSource.java:381-392):
        从 StateTranslationService（CDN 端）获取自定义翻译数据，
        对每项执行 type 正则匹配和 description 处理。
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
            item["type"] = cls._resolve_state_type(unique_name, StateTypeEnum.RESOURCES)
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

    # ══════════════════════════════════════════════════════════════════
    # 数据同步（原 data_sources_init.py → init_state_translation_data）
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def sync_data(cls) -> bool:
        """初始化 StateTranslation（状态翻译）表数据。

        镜像 Java initStateTranslation() (WarframeDataSource.java:364-393):
        Phase 1: 遍历 Export*.json 导出文件 → _parse_all_export_translations()
        Phase 2: 从 CDN 获取自定义数据 → _parse_cdn_translations()
        统一 batch_upsert

        Returns:
            True 表示初始化成功完成；False 表示导出文件下载失败（应跳过后续初始化）。
        """
        from ..init.engine import get_engine
        from ..init.export_downloader import sever_export_files
        from .data_sync import DataSyncService

        logger.info("开始初始化状态翻译数据...")
        await get_engine()

        if not await sever_export_files():
            logger.warning("导出文件下载失败，跳过所有数据初始化")
            return False

        # Phase 1: 从导出文件解析
        all_items = await cls._parse_all_export_translations()

        # Phase 2: 从 CDN 获取自定义数据
        cdn_items = await cls._parse_cdn_translations()
        all_items.extend(cdn_items)

        if not all_items:
            logger.warning("无状态翻译数据可插入")
            return True

        total_upserted = await DataSyncService.batch_upsert(
            model_cls=StateTranslation,
            items=all_items,
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
        total = await StateTranslation.all().count()
        logger.info(f"状态翻译数据初始化完成，共 {total} 条记录（本次处理 {total_upserted} 条）")
        return True

    # ══════════════════════════════════════════════════════════════════
    # 查询
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def get_state_translation(
        cls, unique_name: str
    ) -> str | None:
        """根据唯一名称获取状态翻译名称。

        Args:
            unique_name: 唯一名称。

        Returns:
            翻译后的名称，未找到返回 None。
        """
        try:
            st = await StateTranslation.get(unique_name=unique_name)
            return st.name
        except DoesNotExist:
            return None

    @classmethod
    async def search_state(
        cls, keyword: str, page: int = 1, page_size: int = 20
    ):
        """模糊搜索状态翻译。

        Returns:
            (结果列表, 总数) 的元组。
        """
        offset = (page - 1) * page_size
        qs = StateTranslation.filter(name__contains=keyword)
        total = await qs.count()
        items = await qs.offset(offset).limit(page_size)
        return list(items), total

    @classmethod
    async def batch_translate_by_suffix(
        cls, keywords: set[str]
    ) -> dict[str, str]:
        """批量后缀匹配翻译（供 Relics 初始化使用）。

        镜像 Java RelicsImportUtil.loadTranslationMap():
        1. 通过 endswith OR 查询从 DB 过滤候选行
        2. 预建后缀索引（最后 1~3 段路径 → name）
        3. O(1) 查找每个 keyword，返回 {keyword: name} 映射

        复杂度：O(N + M)，N=匹配行数，M=关键词数。
        后缀索引假设 keyword 是路径段拼接而成（如 "Seg1/Seg2/Seg3"）；
        非路径段 keyword 可能不在索引中（但调用方始终使用路径段）。

        Args:
            keywords: 关键词集合

        Returns:
            {keyword: translated_name} 映射，
            未找到翻译的 keyword 不出现在结果中。
        """
        if not keywords:
            return {}

        # 分批构建 OR 查询，避免单个 Q 树层级过深导致 TortoiseORM 递归溢出
        # 每批最多 80 个 ENDSWITH 条件，合并各批结果
        _Q_BATCH_SIZE = 80
        kw_list = list(keywords)
        all_rows: list[tuple[str, str]] = []

        for i in range(0, len(kw_list), _Q_BATCH_SIZE):
            batch = kw_list[i:i + _Q_BATCH_SIZE]
            q = Q()
            for kw in batch:
                q |= Q(uniqueName__endswith=kw)
            rows = await (
                StateTranslation.filter(q)
                .values_list("uniqueName", "name")
            )
            all_rows.extend(rows)

        # 预建后缀索引: {suffix_path_segment: translated_name}
        # 对每条 uniqueName，注册最后 1~min(3, len(parts)) 段路径为 key
        suffix_index: dict[str, str] = {}
        for unique_name, name in all_rows:
            if not unique_name or not name:
                continue
            # 按 / 拆分路径，过滤空段
            parts = [p for p in unique_name.split("/") if p]
            max_len = min(3, len(parts))
            # 从短到长注册后缀：短后缀优先保留，符合"首个匹配"语义
            for length in range(1, max_len + 1):
                suffix = "/".join(parts[-length:])
                if suffix not in suffix_index:
                    suffix_index[suffix] = name

        # O(1) 查找每个关键词
        result: dict[str, str] = {}
        for kw in keywords:
            name = suffix_index.get(kw)
            if name:
                result[kw] = name

        return result
