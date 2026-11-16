"""Warframes service / 战甲服务

提供战甲（Warframes）与战甲技能（WarframeAbility）的数据同步。
数据来源：官方导出文件 ExportWarframes_zh.json。
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import orjson

from astrbot.api import logger

from ..model.export.warframes import WarframeAbility, Warframes

#: 同一进程内战甲同步互斥。
#: 启动导入与后台数据管理的「同步」按钮可能并发触发；技能表没有唯一约束，
#: 两个 delete + create 交错（都在对方插入前完成删除）会插入两份完整列表。
#: 战甲表的 batch_upsert 是按键幂等的，不需要锁，只锁技能重建这一段。
_SYNC_LOCK = asyncio.Lock()

#: 战甲表需要 upsert 的字段（``uniqueName`` 是主键，不列入）。
_WARFRAME_UPDATE_FIELDS: tuple[str, ...] = (
    "name",
    "parentName",
    "description",
    "health",
    "shield",
    "armor",
    "stamina",
    "power",
    "codexSecret",
    "masteryReq",
    "sprintSpeed",
    "productCategory",
    "passiveDescription",
    "longDescription",
    "exalted",
    "excludeFromCodex",
)

#: 技能批量写入的分批大小。
_ABILITY_BATCH_SIZE = 200


class WarframesService:
    """战甲服务。"""

    # ══════════════════════════════════════════════════════════════════
    # 私有：ExportWarframes 解析
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    def _parse_export_warframes(
        cls, export_path: str
    ) -> tuple[list[dict], list[dict]]:
        """解析 ExportWarframes_zh.json，拆成战甲行与技能行。

        特殊处理：

        1. ``abilities`` 是嵌套列表，需拆出来单独落 ``warframeability`` 表。
           同一技能会挂在多个战甲上（导出里 508 条技能只有 295 个唯一
           ``abilityUniqueName``），所以技能表用自增主键 + 外键关联，
           不能拿技能名当主键。
        2. ``exalted`` 是字符串列表，模型用 ``TextField`` 存 JSON。

        Args:
            export_path: ExportWarframes_zh.json 的完整路径。

        Returns:
            ``(战甲行列表, 技能行列表)``，技能行已带 ``warframe_id`` 外键值。
        """
        warframes: list[dict] = []
        abilities: list[dict] = []

        raw = orjson.loads(Path(export_path).read_bytes())
        items = raw.get("ExportWarframes", [])
        if not isinstance(items, list):
            return warframes, abilities

        for item in items:
            if not isinstance(item, dict):
                continue
            uid = item.get("uniqueName")
            if not uid:
                continue

            # --- 特殊处理 1: 拆出技能 ---
            for ability in item.pop("abilities", None) or []:
                if not isinstance(ability, dict):
                    continue
                ability_uid = ability.get("abilityUniqueName")
                if not ability_uid:
                    continue
                abilities.append(
                    {
                        "abilityUniqueName": ability_uid,
                        "abilityName": ability.get("abilityName"),
                        "description": ability.get("description"),
                        "warframe_id": uid,
                    }
                )

            # --- 特殊处理 2: exalted 列表序列化 ---
            exalted = item.get("exalted")
            if isinstance(exalted, list):
                item["exalted"] = orjson.dumps(exalted).decode()

            warframes.append(item)

        return warframes, abilities

    # ══════════════════════════════════════════════════════════════════
    # 数据同步
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def sync_data(cls) -> bool:
        """初始化战甲与战甲技能数据。

        Returns:
            True 表示同步完成；导出文件缺失或数据为空时返回 False，
            以便 ``bootstrap`` 的失败统计能捕捉到。
        """
        from ..init.engine import get_engine
        from ..init.export_downloader import ExportDir, resolve_export_filename
        from .data_sync import DataSyncService

        await get_engine()

        filename = await resolve_export_filename("ExportWarframes")
        if not filename:
            logger.warning("未找到 ExportWarframes 导出文件，跳过战甲数据初始化")
            return False

        export_path = Path(ExportDir) / filename
        if not export_path.exists():
            logger.warning(f"{filename} 不存在，跳过战甲数据初始化")
            return False

        logger.info(f"从 {filename} 解析战甲数据...")
        warframes, abilities = cls._parse_export_warframes(str(export_path))
        if not warframes:
            logger.warning("战甲数据为空，跳过")
            return False
        if not abilities:
            # 导出里有战甲却没有任何技能：多半是下载不完整、或来源格式变了。
            # 若照常重建，会先删光现有技能、再跳过插入、并返回 True——静默清库。
            # 这里整次同步按失败处理，保留库里的旧数据，等下次启动重试。
            logger.warning(
                f"{filename} 未解析出任何战甲技能，视为异常导出，跳过战甲同步"
            )
            return False

        logger.info(
            f"已解析 {filename}: {len(warframes)} 个战甲、{len(abilities)} 条技能"
        )

        await DataSyncService.batch_upsert(
            model_cls=Warframes,
            items=warframes,
            key_field="uniqueName",
            build_instance=lambda item: Warframes(**item),
            update_fields=list(_WARFRAME_UPDATE_FIELDS),
        )

        # 技能是纯参考数据，且同一技能可挂多个战甲——单键 upsert 表达不了
        # 这种多对一关系，直接全量重建最稳妥（也顺带刷新技能文案）。
        async with _SYNC_LOCK:
            await cls._rebuild_abilities(abilities)

        total_w = await Warframes.all().count()
        total_a = await WarframeAbility.all().count()
        logger.info(
            f"战甲数据初始化完成，共 {total_w} 个战甲、{total_a} 条技能"
        )
        return True

    @classmethod
    async def _rebuild_abilities(cls, abilities: list[dict]) -> None:
        """技能表全量重建：删除与重建在**同一事务**里。

        否则 ``bulk_create`` 失败（或进程中断）时删除已提交，技能表留空，
        调用方看到的是「无技能」而不是「同步失败」——与
        ``data_sync`` / ``relics`` / ``reward`` 的多步写约定一致。
        """
        from tortoise.transactions import in_transaction

        async with in_transaction():
            await WarframeAbility.all().delete()
            if abilities:
                await WarframeAbility.bulk_create(
                    [WarframeAbility(**item) for item in abilities],
                    batch_size=_ABILITY_BATCH_SIZE,
                )
