"""Exprot repository / 导出数据访问层

包含所有 exprot 子包下的模型。
"""
from __future__ import annotations

from typing import Optional

from tortoise.exceptions import DoesNotExist

from ..model.export.customs import Customs
from ..model.export.mod_set import ModSet
from ..model.export.night_wave import NightWave
from ..model.export.relics import Relics
from ..model.export.relic_rewards import RelicRewards
from ..model.export.sentinels import Sentinels
from ..model.export.upgrades import Upgrades
from ..model.export.warframes import Warframes, WarframeAbility
from ..model.export.weapons import Weapons
from ..model.export.reward.reward import Reward
from ..model.export.reward.reward_pool import RewardPool
from .base import BaseRepository


class CustomsRepository(BaseRepository[Customs]):
    """外观数据访问对象。"""

    def __init__(self):
        super().__init__(Customs)

    async def find_by_unique_name(
        self, unique_name: str
    ) -> Optional[Customs]:
        """根据唯一名称查找。"""
        try:
            return await Customs.get(unique_name=unique_name)
        except DoesNotExist:
            return None


class ModSetRepository(BaseRepository[ModSet]):
    """MOD 套装数据访问对象。"""

    def __init__(self):
        super().__init__(ModSet)

    async def find_by_unique_name(
        self, unique_name: str
    ) -> Optional[ModSet]:
        """根据唯一名称查找。"""
        try:
            return await ModSet.get(unique_name=unique_name)
        except DoesNotExist:
            return None


class NightWaveRepository(BaseRepository[NightWave]):
    """电波任务数据访问对象。"""

    def __init__(self):
        super().__init__(NightWave)

    async def find_by_unique_name(
        self, unique_name: str
    ) -> Optional[NightWave]:
        """根据唯一名称查找。"""
        try:
            return await NightWave.get(unique_name=unique_name)
        except DoesNotExist:
            return None


class RelicsRepository(BaseRepository[Relics]):
    """遗物数据访问对象。"""

    def __init__(self):
        super().__init__(Relics)

    async def find_by_unique_name(
        self, unique_name: str
    ) -> Optional[Relics]:
        """根据唯一名称查找（含关联的 RelicRewards）。"""
        try:
            return await Relics.get(unique_name=unique_name).prefetch_related("relic_rewards")
        except DoesNotExist:
            return None

    async def search_by_name(
        self, keyword: str, offset: int = 0, limit: int = 100
    ):
        """按名称模糊搜索遗物。"""
        qs = Relics.filter(name__contains=keyword)
        total = await qs.count()
        items = await qs.offset(offset).limit(limit)
        return list(items), total


class RelicRewardsRepository(BaseRepository[RelicRewards]):
    """遗物奖励数据访问对象。"""

    def __init__(self):
        super().__init__(RelicRewards)

    async def find_by_relic(
        self, relics_id: str
    ) -> list[RelicRewards]:
        """根据关联的遗物 ID 查找奖励列表。"""
        return await RelicRewards.filter(relics_id=relics_id)


class SentinelsRepository(BaseRepository[Sentinels]):
    """守护/宠物数据访问对象。"""

    def __init__(self):
        super().__init__(Sentinels)

    async def find_by_unique_name(
        self, unique_name: str
    ) -> Optional[Sentinels]:
        """根据唯一名称查找。"""
        try:
            return await Sentinels.get(unique_name=unique_name)
        except DoesNotExist:
            return None


class UpgradesRepository(BaseRepository[Upgrades]):
    """MOD / 升级组件数据访问对象。"""

    def __init__(self):
        super().__init__(Upgrades)

    async def find_by_unique_name(
        self, unique_name: str
    ) -> Optional[Upgrades]:
        """根据唯一名称查找。"""
        try:
            return await Upgrades.get(unique_name=unique_name)
        except DoesNotExist:
            return None


class WarframesRepository(BaseRepository[Warframes]):
    """战甲数据访问对象。"""

    def __init__(self):
        super().__init__(Warframes)

    async def find_by_unique_name(
        self, unique_name: str
    ) -> Optional[Warframes]:
        """根据唯一名称查找（含关联的 Abilities）。"""
        try:
            return await Warframes.get(unique_name=unique_name).prefetch_related("abilities")
        except DoesNotExist:
            return None


class WarframeAbilityRepository(BaseRepository[WarframeAbility]):
    """战甲技能数据访问对象。"""

    def __init__(self):
        super().__init__(WarframeAbility)

    async def find_by_warframe(
        self, warframe_unique_name: str
    ) -> list[WarframeAbility]:
        """根据所属战甲查找技能列表。"""
        return await WarframeAbility.filter(warframe_id=warframe_unique_name)


class WeaponsRepository(BaseRepository[Weapons]):
    """武器数据访问对象。"""

    def __init__(self):
        super().__init__(Weapons)

    async def find_by_unique_name(
        self, unique_name: str
    ) -> Optional[Weapons]:
        """根据唯一名称查找。"""
        try:
            return await Weapons.get(unique_name=unique_name)
        except DoesNotExist:
            return None

    async def search_by_name(
        self, keyword: str, offset: int = 0, limit: int = 100
    ):
        """按名称模糊搜索武器。"""
        qs = Weapons.filter(name__contains=keyword)
        total = await qs.count()
        items = await qs.offset(offset).limit(limit)
        return list(items), total


class RewardRepository(BaseRepository[Reward]):
    """具体奖励数据访问对象。"""

    def __init__(self):
        super().__init__(Reward)

    async def find_by_item(
        self, item_name: str
    ) -> list[Reward]:
        """根据奖励物品名称查找。"""
        return await Reward.filter(item__contains=item_name)


class RewardPoolRepository(BaseRepository[RewardPool]):
    """奖励池数据访问对象。"""

    def __init__(self):
        super().__init__(RewardPool)

    async def find_by_unique_name(
        self, unique_name: str
    ) -> Optional[RewardPool]:
        """根据唯一名称查找（含关联的 Rewards）。"""
        try:
            return await RewardPool.get(unique_name=unique_name).prefetch_related("rewards")
        except DoesNotExist:
            return None


# 模块级单例
customs_repo = CustomsRepository()
mod_set_repo = ModSetRepository()
night_wave_repo = NightWaveRepository()
relics_repo = RelicsRepository()
relic_rewards_repo = RelicRewardsRepository()
sentinels_repo = SentinelsRepository()
upgrades_repo = UpgradesRepository()
warframes_repo = WarframesRepository()
warframe_ability_repo = WarframeAbilityRepository()
weapons_repo = WeaponsRepository()
reward_repo = RewardRepository()
reward_pool_repo = RewardPoolRepository()
