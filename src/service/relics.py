"""Relics service / 遗物服务

提供遗物（Relics）的数据同步和查询功能。
包含 ExportRelicArcane JSON 的完整数据管道：解析 + 翻译 + 持久化 + M2M diff。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from astrbot.api import logger

if TYPE_CHECKING:
    from ..model.export.relics import Relics

# Warframe 部件术语中文翻译（镜像 Java translateReward 中的 replace 链）
_WARFRAME_PART_TRANSLATIONS: dict[str, str] = {
    "Blueprint": "蓝图",
    "Systems": "系统",
    "Chassis": "机体",
    "Helmet": "头部神经光元",
}


class RelicsService:
    """遗物服务。"""

    # ══════════════════════════════════════════════════════════════════
    # 私有：ExportRelicArcane 解析（原 export_parsers.py）
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    def _parse_export_relic_arcane_to_relics(cls, export_path: str) -> list[dict]:
        """解析 ExportRelicArcane_zh.json，返回 Relics 兼容的 dict 列表。

        镜像 Java RelicsImportUtil.readRelicsFromFile() + Jackson 反序列化:

        JSON 结构:
            {
              "ExportRelicArcane": [
                {
                  "uniqueName": "/Lotus/Relics/...",
                  "name": "丽斯 A1 遗物",
                  "codexSecret": false,
                  "description": "...",
                  "relicRewards": [
                    {"rewardName": "/Lotus/Weapons/...", "rarity": "Common", "tier": 1, "itemCount": 1},
                    ...
                  ]
                },
                ...
              ]
            }

        Args:
            export_path: ExportRelicArcane_zh.json 的完整路径

        Returns:
            list[dict]: 每个 dict 包含 Relics 字段 + "rewards" 子列表
        """
        result: list[dict] = []
        raw = json.loads(Path(export_path).read_text(encoding="utf-8"))
        items = raw.get("ExportRelicArcane", [])
        if not isinstance(items, list):
            return result

        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not name:
                continue

            # 提取基础字段
            relic_dict = {
                "uniqueName": item.get("uniqueName", ""),
                "name": name,
                "codexSecret": item.get("codexSecret"),
                "description": item.get("description"),
                "rewards": [],  # 子列表
            }

            # 提取嵌套的 relicRewards
            rewards = item.get("relicRewards")
            if isinstance(rewards, list):
                for r in rewards:
                    if isinstance(r, dict):
                        relic_dict["rewards"].append({
                            "rewardName": r.get("rewardName"),
                            "rarity": r.get("rarity"),
                            "tier": r.get("tier"),
                            "itemCount": r.get("itemCount"),
                        })

            result.append(relic_dict)

        return result

    # ══════════════════════════════════════════════════════════════════
    # 私有：翻译辅助
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def _translate_relic_rewards(cls, relics_data: list[dict]) -> list[dict]:
        """翻译遗物奖励的 rewardName（镜像 Java translateReward + addToUntranslatedItems）。

        通过 TranslationService.batch_translate_by_suffix() 批量翻译：
        1. 提取每个 rewardName 的最后3个路径段作为关键词
        2. 调用 TranslationService 批量后缀匹配翻译
        3. 替换 rewardName 为翻译名（找不到则保留原文）
        4. 收集未翻译项并返回（供后续导出）

        Returns:
            list[dict]: 未翻译项列表，每项格式 {"uniqueName": str, "name": str, "description": str}
        """
        from ..util.string_utils import get_last_three_segments, split_camel_case
        from .state_translation import StateTranslationService

        # 单次遍历收集所有翻译关键词
        keywords: set[str] = set()
        for item in relics_data:
            for r in item.get("rewards", []):
                if rn := r.get("rewardName"):
                    if kw := get_last_three_segments(rn):
                        keywords.add(kw)

        if not keywords:
            return []

        # 通过 Service 批量翻译
        translation_map = await StateTranslationService.batch_translate_by_suffix(keywords)

        # 单次遍历应用翻译 + 收集未翻译项（去重）
        # 使用 walrus operator (:=) 减少局部变量重复赋值
        untranslated_map: dict[str, dict] = {}  # rewardName → item dict 去重
        for item in relics_data:
            for r in item.get("rewards", []):
                if rn := r.get("rewardName"):
                    if kw := get_last_three_segments(rn):
                        if translated := translation_map.get(kw):
                            r["rewardName"] = translated
                            continue
                    # 未找到翻译，收集（去重）
                    # 生成兜底名称：取路径最后一段 → 驼峰拆分 → WF 术语翻译
                    if rn not in untranslated_map:
                        last_segment = rn.rsplit("/", 1)[-1] if "/" in rn else rn
                        fallback_name = split_camel_case(last_segment)
                        for eng, zh in _WARFRAME_PART_TRANSLATIONS.items():
                            fallback_name = fallback_name.replace(eng, zh)
                        untranslated_map[rn] = {
                            "uniqueName": rn,
                            "name": fallback_name,
                            "description": "",
                        }

        return list(untranslated_map.values())

    @staticmethod
    def _export_untranslated_relic_rewards(untranslated: list[dict]) -> None:
        """导出未翻译的遗物奖励到 JSON 文件（镜像 Java exportUntranslatedItems）。

        保存路径: {get_public_data_path()}/untranslated_relics_rewards.json

        Args:
            untranslated: _translate_relic_rewards() 返回的未翻译项列表
        """
        from ..util import get_public_data_path

        file_path = Path(get_public_data_path()) / "untranslated_relics_rewards.json"
        try:
            file_path.write_text(
                json.dumps(untranslated, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info(
                f"成功导出 {len(untranslated)} 条未翻译遗物奖励到: {file_path}"
            )
        except OSError as e:
            logger.error(f"导出未翻译遗物奖励失败: {e}")

    # ══════════════════════════════════════════════════════════════════
    # 数据同步（原 data_sources_init.py → init_relics_data）
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def sync_data(cls) -> None:
        """初始化 Relics（遗物）表数据（含 M2M 关联的 RelicRewards）。

        镜像 Java RelicsImportUtil.importRelicsData() +
        参照 Python RewardService.sync_data() 的 M2M diff 模式。

        流程:
            1. 解析 ExportRelicArcane JSON
            2. 按 name 去重 + 过滤 codexSecret=true
            3. 翻译 rewardName（查 StateTranslation，尽力而为）
            4. 导出未翻译项到 untranslated_relics_rewards.json
            5. 事务内:
               a. Upsert Relics（通过 DataSyncService.batch_upsert）
               b. 全局 bulk_create RelicRewards (ignore_conflicts=True)
               c. 每 Relic M2M diff (add/remove)
        """
        from tortoise.transactions import in_transaction

        from ..init.engine import get_engine
        from ..init.export_downloader import (
            ExportDir,
            resolve_export_filename,
        )
        from ..model.export.relic_rewards import RelicRewards
        from ..model.export.relics import Relics
        from .data_sync import DataSyncService

        logger.info("从导出文件初始化遗物数据...")
        await get_engine()

        # 1. 解析导出文件
        filename = await resolve_export_filename("ExportRelicArcane")
        if not filename:
            logger.warning("未找到 ExportRelicArcane 导出文件，跳过遗物数据初始化")
            return

        export_path = Path(ExportDir) / filename
        if not export_path.exists():
            logger.warning(f"{filename} 不存在，跳过遗物数据初始化")
            return

        logger.info(f"从 {filename} 解析遗物数据...")
        items = cls._parse_export_relic_arcane_to_relics(str(export_path))
        if not items:
            logger.warning("遗物数据为空，跳过")
            return

        # 2. 按 name 去重
        seen_names: set[str] = set()
        deduped: list[dict] = []
        for item in items:
            name = item.get("name")
            if name and name not in seen_names:
                seen_names.add(name)
                deduped.append(item)
        logger.info(f"已解析 {filename}: {len(items)} 条，去重后 {len(deduped)} 条")

        # 3. 过滤 codexSecret=true
        relics_data = [item for item in deduped if not item.get("codexSecret")]
        logger.info(f"过滤机密遗物后: {len(relics_data)} 条")

        # 4. 翻译 rewardName（尽力而为，收集未翻译项）
        untranslated = await cls._translate_relic_rewards(relics_data)

        # 5. 导出未翻译项到 JSON 文件
        if untranslated:
            cls._export_untranslated_relic_rewards(untranslated)

        # 6. 事务内: Upsert Relics + M2M diff
        new_relic_count = 0
        added_count = 0
        removed_count = 0

        async with in_transaction():
            # 6a. Upsert Relics
            new_relic_count = await DataSyncService.batch_upsert(
                model_cls=Relics,
                items=[
                    {
                        "uniqueName": item["uniqueName"],
                        "name": item["name"],
                        "codexSecret": item.get("codexSecret"),
                        "description": item.get("description"),
                    }
                    for item in relics_data
                ],
                key_field="uniqueName",
                build_instance=lambda item: Relics(
                    uniqueName=item["uniqueName"],
                    name=item.get("name"),
                    codexSecret=item.get("codexSecret"),
                    description=item.get("description"),
                ),
                update_fields=["name", "codexSecret", "description"],
                use_transaction=False,  # 外部已有事务
            )

            # 6b. 全局 bulk_create RelicRewards (确定性哈希主键 + ignore_conflicts 天然去重)
            all_reward_instances: list[RelicRewards] = []
            for item in relics_data:
                for r in item.get("rewards", []):
                    rid = RelicRewards.make_id(
                        r["rewardName"], r.get("rarity"), r.get("tier"), r.get("itemCount")
                    )
                    all_reward_instances.append(RelicRewards(
                        id=rid,
                        rewardName=r["rewardName"],
                        rarity=r.get("rarity"),
                        tier=r.get("tier"),
                        itemCount=r.get("itemCount"),
                    ))
            if all_reward_instances:
                await RelicRewards.bulk_create(
                    all_reward_instances, ignore_conflicts=True
                )

            # 6c. 每 Relic M2M diff
            # 使用 prefetch_related 一次性预加载所有 M2M 关联，避免 per-relic N+1 查询
            relic_names_list = [item["uniqueName"] for item in relics_data]
            all_relics = {
                r.uniqueName: r
                async for r in Relics.filter(
                    uniqueName__in=relic_names_list
                ).prefetch_related("relic_rewards")
            }

            for item in relics_data:
                relic_name = item["uniqueName"]
                relic = all_relics.get(relic_name)
                if not relic:
                    continue

                # CDN 的 reward ID 集合
                cdn_ids: set[str] = set()
                for r in item.get("rewards", []):
                    cdn_ids.add(
                        RelicRewards.make_id(
                            r["rewardName"], r.get("rarity"), r.get("tier"), r.get("itemCount")
                        )
                    )

                # DB 已有的 M2M reward ID 集合 — 已通过 prefetch_related 预加载，纯内存操作
                db_ids: set[str] = {
                    reward.id for reward in relic.relic_rewards
                }

                # Diff: 新增的 M2M 关联
                new_ids = cdn_ids - db_ids
                if new_ids:
                    new_rewards = await RelicRewards.filter(id__in=list(new_ids))
                    if new_rewards:
                        await relic.relic_rewards.add(*new_rewards)
                        added_count += len(new_rewards)

                # Diff: 移除的 M2M 关联
                removed_ids = db_ids - cdn_ids
                if removed_ids:
                    old_rewards = await RelicRewards.filter(id__in=list(removed_ids))
                    if old_rewards:
                        await relic.relic_rewards.remove(*old_rewards)
                        removed_count += len(old_rewards)

        total_relics = await Relics.all().count()
        total_rewards = await RelicRewards.all().count()
        logger.info(
            f"遗物数据初始化完成，"
            f"共 {total_relics} 个遗物（本次新增 {new_relic_count} 个），"
            f"共 {total_rewards} 条奖励记录"
            f"（新增 {added_count} 条 M2M 关联，移除 {removed_count} 条）"
        )

    # ══════════════════════════════════════════════════════════════════
    # 查询（镜像 Java RelicsService.findAllByRelicNameOrRewardsItemName）
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def find_by_name_or_reward(cls, name: str) -> list[Relics]:
        """多级回退查询遗物 — 按遗物名称或奖励物品名称搜索。

        镜像 Java RelicsService.findAllByRelicNameOrRewardsItemName()：
        1. 精确匹配遗物名称
        2. 模糊匹配遗物名称
        3. 模糊匹配奖励物品名称（通过 M2M 中间表反向查询）
        4. 别名替换（中文→英文）后再次模糊匹配奖励
        5. 全部失败返回空列表

        Args:
            name: 搜索关键词（遗物名称或奖励物品名称）。

        Returns:
            list[Relics]: 匹配的遗物模型列表（已 prefetch 关联奖励），按名称排序。
        """
        from tortoise.expressions import Q

        from ..model.alias import Alias
        from ..model.export.relic_rewards import RelicRewards
        from ..model.export.relics import Relics

        # 空查询 → 返回所有遗物
        if not name or not name.strip():
            return await (
                Relics.all()
                .prefetch_related("relic_rewards")
                .order_by("name")
            )

        name = name.strip()

        # 1. 精确匹配遗物名称
        rs = await (
            Relics.filter(name=name)
            .prefetch_related("relic_rewards")
            .order_by("name")
        )
        if rs:
            return list(rs)

        logger.debug(f"未查询到遗物名称为 '{name}' 的遗物，进行模糊查询")

        # 2. 模糊匹配遗物名称
        rs = await (
            Relics.filter(name__contains=name)
            .prefetch_related("relic_rewards")
            .order_by("name")
        )
        if rs:
            return list(rs)

        logger.debug(f"未查询到包含 '{name}' 的遗物，进行奖励物品的模糊查询")

        # 3. 模糊匹配奖励物品名称（排除 Forma，避免因每个遗物都含 Forma 导致结果膨胀）
        reward_ids = await RelicRewards.filter(
            Q(rewardName__contains=name) & ~Q(rewardName__contains="Forma"),
        ).values_list("id", flat=True)
        if reward_ids:
            rs = await (
                Relics.filter(relic_rewards__id__in=list(reward_ids))
                .distinct()
                .prefetch_related("relic_rewards")
                .order_by("name")
            )
            if rs:
                return list(rs)

        logger.debug(f"未查询到包含 '{name}' 的遗物，使用别名模糊查询奖励列表")

        # 4. 别名替换后再次模糊匹配
        aliases = await Alias.all()
        key = name
        for a in aliases:
            if a.cn and a.cn in key:
                key = key.replace(a.cn, a.en or "")

        if key != name:
            reward_ids = await RelicRewards.filter(
                Q(rewardName__contains=key) & ~Q(rewardName__contains="Forma"),
            ).values_list("id", flat=True)
            if reward_ids:
                rs = await (
                    Relics.filter(relic_rewards__id__in=list(reward_ids))
                    .distinct()
                    .prefetch_related("relic_rewards")
                    .order_by("name")
                )
                if rs:
                    return list(rs)

        logger.debug(f"未找到物品: {name}")
        return []
