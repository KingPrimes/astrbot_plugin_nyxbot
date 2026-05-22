"""NightWave service / 电波任务服务

提供电波任务（NightWave）的数据同步和查询功能。
包含 ExportSortieRewards JSON 中 NightWave 挑战的完整数据管道：解析 + 持久化。
"""
from __future__ import annotations

import json
from pathlib import Path

from astrbot.api import logger

from ..model.export.night_wave import NightWave


class NightWaveService:
    """电波任务服务。"""

    # ══════════════════════════════════════════════════════════════════
    # 私有：NightWave 解析（原 export_parsers.py）
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    def _parse_export_sortie_rewards_to_nightwave(cls, export_path: str) -> list[dict]:
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

    # ══════════════════════════════════════════════════════════════════
    # 数据同步（原 data_sources_init.py → init_night_wave_data）
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def sync_data(cls) -> None:
        """初始化 NightWave（电波任务）表数据 — 从导出文件。

        镜像 Java initNightWave() (WarframeDataSource.java:395-414):
        解析 ExportSortieRewards_zh.json → ExportNightwave.challenges
        → 批量 upsert 到 NightWave 表
        """
        from ..init.engine import get_engine
        from ..init.export_downloader import (
            ExportDir,
            resolve_export_filename,
        )
        from .data_sync import DataSyncService

        await get_engine()

        filename = await resolve_export_filename("ExportSortieRewards")
        if not filename:
            logger.warning("未找到 ExportSortieRewards 导出文件，跳过电波任务数据初始化")
            return

        export_path = Path(ExportDir) / filename
        if not export_path.exists():
            logger.warning(f"{filename} 不存在，跳过电波任务数据初始化")
            return

        logger.info(f"从 {filename} 解析电波任务数据...")
        items = cls._parse_export_sortie_rewards_to_nightwave(str(export_path))
        if not items:
            logger.warning("电波任务数据为空，跳过")
            return

        logger.info(f"已解析 {filename}: {len(items)} 条")
        total_upserted = await DataSyncService.batch_upsert(
            model_cls=NightWave,
            items=items,
            key_field="uniqueName",
            build_instance=lambda item: NightWave(**item),
            update_fields=["name", "description", "standing", "required"],
        )
        total = await NightWave.all().count()
        logger.info(f"电波任务数据初始化完成，共 {total} 条记录（本次处理 {total_upserted} 条）")
