"""Weapons service / 武器服务

提供武器的数据同步和查询功能。
包含 ExportWeapons JSON 的完整数据管道：解析 + 持久化。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from astrbot.api import logger

from ..model.export.weapons import Weapons
from ..util import to_title_case


class WeaponsService:
    """武器服务。"""

    # ══════════════════════════════════════════════════════════════════
    # 私有：ExportWeapons 解析（原 export_parsers.py）
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def _extract_weapon_english_name(item: dict) -> str:
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
        if name and name.upper() == "MK1-" and e_name and e_name != desc and e_name.upper() != "MK1-":
            return f"Mk1-{e_name}"

        # 如果提取到的英文名与 description 相同，说明提取失败（Java L150-152）
        if e_name and e_name == desc:
            return ""

        return e_name

    @classmethod
    def _parse_export_weapons_to_weapons(cls, export_path: str) -> list[dict]:
        """解析 ExportWeapons_zh.json，返回 Weapons 兼容的 dict 列表。

        镜像 Java parsingExportJson("ExportWeapons_zh.json", "ExportWeapons", Weapons.class)
        + forEach contEnglishName() (WarframeDataSource.java:438-439):

        特殊处理:
        1. damagePerShot: Java 是 List<Double> / Python 模型是 TextField
           → 需 json.dumps() 序列化为 JSON 字符串
        2. englishName: 从 description 中提取 （英文：...）→ to_title_case() 转换
           → 调用 _extract_weapon_english_name()

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
            item["englishName"] = cls._extract_weapon_english_name(item)

            result.append(item)

        return result

    # ══════════════════════════════════════════════════════════════════
    # 数据同步（原 data_sources_init.py → init_weapons_data）
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def sync_data(cls) -> None:
        """初始化武器数据 — 从导出文件。

        镜像 Java initWeapons() (WarframeDataSource.java:436-442):
        Phase 1: 解析 ExportWeapons_zh.json → Weapons dicts
        （含 damagePerShot 序列化 + englishName 提取）
        统一 batch_upsert
        """
        from ..init.engine import get_engine
        from ..init.export_downloader import (
            ExportDir,
            resolve_export_filename,
        )
        from .data_sync import DataSyncService

        await get_engine()

        filename = await resolve_export_filename("ExportWeapons")
        if not filename:
            logger.warning("未找到 ExportWeapons 导出文件，跳过武器数据初始化")
            return

        export_path = Path(ExportDir) / filename
        if not export_path.exists():
            logger.warning(f"{filename} 不存在，跳过武器数据初始化")
            return

        logger.info(f"从 {filename} 解析武器数据...")
        items = cls._parse_export_weapons_to_weapons(str(export_path))
        if not items:
            logger.warning("武器数据为空，跳过")
            return

        logger.info(f"已解析 {filename}: {len(items)} 条")
        total_upserted = await DataSyncService.batch_upsert(
            model_cls=Weapons,
            items=items,
            key_field="uniqueName",
            build_instance=lambda item: Weapons(**item),
            update_fields=[
                "name", "codexSecret", "damagePerShot", "totalDamage",
                "description", "englishName", "criticalChance",
                "criticalMultiplier", "procChance", "fireRate",
                "masteryReq", "productCategory", "slot", "accuracy",
                "omegaAttenuation", "maxLevelCap", "noise", "trigger",
                "magazineSize", "reloadTime", "sentinel", "multishot",
            ],
        )
        total = await Weapons.all().count()
        logger.info(f"武器数据初始化完成，共 {total} 条记录（本次处理 {total_upserted} 条）")
