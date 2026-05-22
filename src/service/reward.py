"""Reward service / 奖励服务

提供奖励池（RewardPool）的数据同步功能。
包含 RewardPool + Reward M2M 关联的完整数据管道。
"""
from __future__ import annotations

from tortoise.transactions import in_transaction

from astrbot.api import logger

from ..api import CdnClient
from ..model.export.reward.reward import Reward
from ..model.export.reward.reward_pool import RewardPool


class RewardService:
    """奖励服务。"""

    @classmethod
    async def sync_data(cls) -> None:
        """初始化 RewardPool（奖励池）表数据 — 从 CDN，含嵌套 Rewards。

        使用增量 diff 模式管理 RewardPool ↔ Reward 的 M2M 关联：
        - Phase 1: 按 uniqueName 去重，插入新的 RewardPool
        - Phase 2: 批量插入 Reward + M2M diff（新增/移除关联）
        - 全部在 in_transaction() 中执行以保证原子性
        """
        from ..init.engine import get_engine

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

        # Phase 2: 批量插入 Reward + 建立 M2M 关联（增量 diff 模式）
        # ─────────────────────────────────────────────────────────────
        # 策略：
        #   Reward.id = SHA-256(item∥rarity∥itemCount)[:16]（确定性哈希）
        #   a) 全局 bulk_create(ignore_conflicts=True) 插入所有 Reward
        #      — 相同三元组只存一行，跨 Pool 共享
        #   b) 每 Pool 拉取已有 M2M 的 ID 集合 → 与 CDN 计算集合 diff
        #   c) new_ids: Reward 已存在（步骤 a 保证）→ add() 建立 M2M
        #   d) removed_ids: remove() 解除 M2M → 不删除 Reward（可能被其他 Pool 引用）
        # ─────────────────────────────────────────────────────────────

        added_count = 0
        removed_count = 0

        async with in_transaction():

            # 2a. 全局批量插入（确定性哈希主键 + ignore_conflicts 天然去重）
            all_reward_instances: list[Reward] = []
            for item in data:
                for r in item.get("rewards", []):
                    rid = Reward.make_id(
                        r["item"], r.get("rarity"), r.get("itemCount")
                    )
                    all_reward_instances.append(Reward(
                        id=rid,
                        item=r["item"],
                        rarity=r.get("rarity"),
                        itemCount=r.get("itemCount"),
                    ))
            if all_reward_instances:
                await Reward.bulk_create(
                    all_reward_instances, ignore_conflicts=True
                )

            # 2b. 每 Pool 增量 diff M2M 关联
            all_pools = {
                p.uniqueName: p
                async for p in RewardPool.filter(
                    uniqueName__in=[item["uniqueName"] for item in data]
                )
            }

            for item in data:
                pool_name = item["uniqueName"]
                pool = all_pools.get(pool_name)
                if not pool:
                    continue

                # CDN 的 reward ID 集合
                cdn_ids: set[str] = set()
                for r in item.get("rewards", []):
                    cdn_ids.add(
                        Reward.make_id(r["item"], r.get("rarity"), r.get("itemCount"))
                    )

                # DB 已有的 M2M reward ID 集合
                db_ids: set[str] = {
                    row[0]
                    async for row in pool.rewards.all().values_list("id", flat=True)
                }

                # Diff: 新增的 M2M 关联
                new_ids = cdn_ids - db_ids
                if new_ids:
                    new_rewards = await Reward.filter(id__in=list(new_ids))
                    if new_rewards:
                        await pool.rewards.add(*new_rewards)
                        added_count += len(new_rewards)

                # Diff: 移除的 M2M 关联
                removed_ids = db_ids - cdn_ids
                if removed_ids:
                    old_rewards = await Reward.filter(id__in=list(removed_ids))
                    if old_rewards:
                        await pool.rewards.remove(*old_rewards)
                        removed_count += len(old_rewards)

        total_pools = await RewardPool.all().count()
        total_rewards = await Reward.all().count()
        logger.info(
            f"奖励池数据初始化完成，"
            f"共 {total_pools} 个奖励池（本次新增 {new_pool_count} 个），"
            f"共 {total_rewards} 条奖励记录"
            f"（新增 {added_count} 条 M2M 关联，移除 {removed_count} 条）"
        )
