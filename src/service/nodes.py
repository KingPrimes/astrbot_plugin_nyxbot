"""Nodes service / 星图节点服务

提供星图节点的数据同步和查询功能。
包含 ExportRegions JSON 的完整数据管道：解析 + 持久化。
"""
from __future__ import annotations

import json
from pathlib import Path

from astrbot.api import logger

from ..model.export.nodes import Nodes


class NodesService:
    """星图节点服务。"""

    # ══════════════════════════════════════════════════════════════════
    # 私有：ExportRegions 解析（原 export_parsers.py）
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    def _parse_export_regions_to_nodes(cls, export_path: str) -> list[dict]:
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

    # ══════════════════════════════════════════════════════════════════
    # 数据同步（原 data_sources_init.py → init_nodes_data）
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def sync_data(cls) -> None:
        """初始化星图节点数据 — 从导出文件 + CDN。

        镜像 Java initNodes() (WarframeDataSource.java:416-426):
        Phase 1: 解析 ExportRegions_zh.json → Nodes dicts
        Phase 2: 从 CDN 获取自定义 Nodes 数据
        统一 batch_upsert
        """
        from ..api import CdnClient
        from ..init.engine import get_engine
        from ..init.export_downloader import ExportDir, resolve_export_filename
        from .data_sync import DataSyncService

        await get_engine()

        all_items: list[dict] = []

        # Phase 1: 从导出文件解析
        filename = await resolve_export_filename("ExportRegions")
        if filename:
            export_path = Path(ExportDir) / filename
            if export_path.exists():
                logger.info(f"从 {filename} 解析星图节点数据...")
                items = cls._parse_export_regions_to_nodes(str(export_path))
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

        total_upserted = await DataSyncService.batch_upsert(
            model_cls=Nodes,
            items=all_items,
            key_field="uniqueName",
            build_instance=lambda item: Nodes(**item),
            update_fields=[
                "name", "systemName", "systemIndex", "nodeType",
                "masteryReq", "missionIndex", "factionIndex",
                "minEnemyLevel", "maxEnemyLevel",
            ],
        )
        total = await Nodes.all().count()
        logger.info(f"星图节点数据初始化完成，共 {total} 条记录（本次处理 {total_upserted} 条）")
