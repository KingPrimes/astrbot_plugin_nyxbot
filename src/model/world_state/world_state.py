"""
WorldState Model / 世界状态顶层模型

对应 Java: WorldState.java
聚合所有 WorldState 子模型，约 40 个字段。
计算属性（周期模型）通过 @property 按需构造。
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from ...wenum.world_state import SyndicateEnum
from .active_mission import ActiveMission
from .alert import Alert
from .cambion_cycle import CambionCycle
from .cetus_cycle import CetusCycle
from .conquest import Conquest
from .construction_projects import ConstructionProjects
from .daily_deals import DailyDeals
from .descent import Descent
from .duvalier_cycle import DuvalierCycle
from .earth_cycle import EarthCycle
from .endless_xp_choices import EndlessXpChoices
from .endless_xp_schedule import EndlessXpSchedule
from .event import Event
from .experiment_recommended import ExperimentRecommended
from .featured_guilds import FeaturedGuilds
from .flash_sale import FlashSale
from .global_upgrade import GlobalUpgrade
from .goal import Goal
from .hub_events import HubEvents
from .in_game_market import InGameMarket
from .invasion import Invasion
from .known_calendar_seasons import KnownCalendarSeasons
from .library_info import LibraryInfo
from .lite_sortie import LiteSorite
from .node_override import NodeOverride
from .prime_access_availability import PrimeAccessAvailability
from .prime_vault_trader import PrimeVaultTrader
from .pvp_challenge_instance import PVPChallengeInstance
from .season_info import SeasonInfo
from .sortie import Sortie
from .steel_path_offering import SteelPathOffering
from .syndicate_mission import SyndicateMission
from .vallis_cycle import VallisCycle
from .void_storms import VoidStorms
from .void_trader import VoidTrader
from .zariman_cycle import ZarimanCycle


class WorldState(BaseModel):
    """世界状态 / World State

    对应 Java: WorldState
    顶层聚合模型，包含所有子模型。
    周期属性为 @property 计算属性（按需构造，不参与 JSON 序列化）。
    """

    # === JSON 反序列化字段 / JSON-deserialized fields ===

    # 裂隙任务 / Void Fissures
    active_missions: list[ActiveMission] = Field(default_factory=list, alias="ActiveMissions")
    # 警报任务 / Alerts
    alerts: list[Alert] = Field(default_factory=list, alias="Alerts")
    # 版本标签 / Build Label
    build_label: str | None = Field(default=None, alias="BuildLabel")
    # 征服 / Conquests
    conquests: list[Conquest] = Field(default_factory=list, alias="Conquests")
    # 建设项目 / Construction Projects
    construction_projects: list[ConstructionProjects] = Field(default_factory=list, alias="ConstructionProjects")
    # 每日特惠 / Daily Deals
    daily_deals: list[DailyDeals] = Field(default_factory=list, alias="DailyDeals")
    # 下降 / Descents
    descents: list[Descent] = Field(default_factory=list, alias="Descents")
    # 双衍王境奖励 / Duviri Endless XP Choices
    endless_xp_choices: list[EndlessXpChoices] = Field(default_factory=list, alias="EndlessXpChoices")
    # 双衍王境奖励排期 / Duviri Endless XP Schedule
    endless_xp_schedule: list[EndlessXpSchedule] = Field(default_factory=list, alias="EndlessXpSchedule")
    # 新闻/活动 / Events
    events: list[Event] = Field(default_factory=list, alias="Events")
    # 实验推荐 / Experiment Recommended
    experiment_recommended: list[ExperimentRecommended] = Field(default_factory=list, alias="ExperimentRecommended")
    # 精选氏族 / Featured Guilds
    featured_guilds: list[FeaturedGuilds] = Field(default_factory=list, alias="FeaturedGuilds")
    # 闪购 / Flash Sales
    flash_sales: list[FlashSale] = Field(default_factory=list, alias="FlashSales")
    # SKU 促销 / SKU Sales
    sku_sales: list = Field(default_factory=list, alias="SkuSales")
    # 强制登出版本号 / Force Logout Version
    force_logout_version: int | None = Field(default=None, alias="ForceLogoutVersion")
    # 全局升级 / Global Upgrades
    global_upgrades: list[GlobalUpgrade] = Field(default_factory=list, alias="GlobalUpgrades")
    # 活动目标 / Goals
    goals: list[Goal] = Field(default_factory=list, alias="Goals")
    # 枢纽事件 / Hub Events
    hub_events: list[HubEvents] = Field(default_factory=list, alias="HubEvents")
    # 游戏内商城 / In-Game Market
    in_game_market: InGameMarket | None = Field(default=None, alias="InGameMarket")
    # 入侵 / Invasions
    invasions: list[Invasion] = Field(default_factory=list, alias="Invasions")
    # 1999日历 / Known Calendar Seasons
    known_calendar_seasons: list[KnownCalendarSeasons] = Field(default_factory=list, alias="KnownCalendarSeasons")
    # 图书馆信息 / Library Info
    library_info: LibraryInfo | None = Field(default=None, alias="LibraryInfo")
    # 执刑官猎杀 / Lite Sorties (Archon Hunt)
    lite_sorties: list[LiteSorite] = Field(default_factory=list, alias="LiteSorties")
    # 手机版本 / Mobile Version
    mobile_version: str | None = Field(default=None, alias="MobileVersion")
    # 节点覆盖 / Node Overrides
    node_overrides: list[NodeOverride] = Field(default_factory=list, alias="NodeOverrides")
    # 瓦奇娅火星集市 / Prime Vault Traders
    prime_vault_traders: list[PrimeVaultTrader] = Field(default_factory=list, alias="PrimeVaultTraders")
    # Prime Access 可用性 / Prime Access Availability
    prime_access_availability: PrimeAccessAvailability | None = Field(default=None, alias="PrimeAccessAvailability")
    # Prime Vault 可用性列表 / Prime Vault Availabilities
    prime_vault_availabilities: list[bool] = Field(default_factory=list, alias="PrimeVaultAvailabilities")
    # Prime Token 可用性 / Prime Token Availability
    prime_token_availability: bool | None = Field(default=None, alias="PrimeTokenAvailability")
    # 项目百分比 / Project Percentage
    project_pct: list[float] = Field(default_factory=list, alias="ProjectPct")
    # 午夜电波 / Season Info (Nightwave)
    season_info: SeasonInfo | None = Field(default=None, alias="SeasonInfo")
    # 突击 / Sorties
    sorties: list[Sortie] = Field(default_factory=list, alias="Sorties")
    # 集团任务 / Syndicate Missions
    syndicate_missions: list[SyndicateMission] = Field(default_factory=list, alias="SyndicateMissions")
    # 服务器时间 / Server Time (milliseconds)
    time: int | None = Field(default=None, alias="Time")
    # 临时字段 / Tmp
    tmp: str | None = Field(default=None, alias="Tmp")
    # API 版本 / API Version
    version: int | None = Field(default=None, alias="Version")
    # 虚空风暴 / Void Storms (Railjack)
    void_storms: list[VoidStorms] = Field(default_factory=list, alias="VoidStorms")
    # 虚空商人 / Void Traders (Baro Ki'Teer)
    void_traders: list[VoidTrader] = Field(default_factory=list, alias="VoidTraders")
    # 世界种子 / World Seed
    world_seed: str | None = Field(default=None, alias="WorldSeed")
    # PVP 挑战实例 / PVP Challenge Instances
    pvp_challenge_instances: list[PVPChallengeInstance] = Field(default_factory=list, alias="PVPChallengeInstances")
    # PVP 替代模式 / PVP Alternative Modes
    pvp_alternative_modes: list = Field(default_factory=list, alias="PVPAlternativeModes")
    # PVP 活跃锦标赛 / PVP Active Tournaments
    pvp_active_tournaments: list = Field(default_factory=list, alias="PVPActiveTournaments")
    # Twitch 促销 / Twitch Promos
    twitch_promos: list = Field(default_factory=list, alias="TwitchPromos")
    # 持续敌人 / Persistent Enemies
    persistent_enemies: list = Field(default_factory=list, alias="PersistentEnemies")

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}

    # === 计算属性 / Computed cycle properties ===

    @property
    def earth_cycle(self) -> EarthCycle:
        """地球昼夜循环 / Earth Day/Night Cycle"""
        return EarthCycle()

    @property
    def steel_path(self) -> SteelPathOffering:
        """钢铁之路奖励轮换 / Steel Path Offering (pure computed)"""
        return SteelPathOffering()

    @property
    def cetus_cycle(self) -> CetusCycle:
        """夜灵平原昼夜循环 / Cetus (Plains of Eidolon) Cycle"""
        end_ms = self._get_bounties_end_date(SyndicateEnum.CetusSyndicate)
        return CetusCycle(end_ms)

    @property
    def cambion_cycle(self) -> CambionCycle:
        """魔胎之境循环 / Cambion Drift Cycle"""
        return CambionCycle(self.cetus_cycle)

    @property
    def vallis_cycle(self) -> VallisCycle:
        """奥布山谷冷暖循环 / Orb Vallis Cycle"""
        return VallisCycle()

    @property
    def duvalier_cycle(self) -> DuvalierCycle:
        """双衍王境情绪循环 / Duviri Mood Cycle"""
        return DuvalierCycle(self.endless_xp_choices)

    @property
    def zariman_cycle(self) -> ZarimanCycle:
        """扎里曼轮换循环 / Zariman Rotation Cycle"""
        end_ms = self._get_bounties_end_date(SyndicateEnum.ZarimanSyndicate)
        return ZarimanCycle(end_ms)

    def _get_bounties_end_date(self, key: SyndicateEnum) -> int:
        """从 syndicate_missions 中获取指定集团的赏金结束时间（毫秒）

        对应 Java: WorldState.getBountiesEndDate(SyndicateEnum)

        Args:
            key: 目标集团枚举值

        Returns:
            毫秒时间戳，未找到时返回当前时间戳
        """
        import time

        for mission in self.syndicate_missions:
            if mission.tag == key and mission.expiry is not None:
                return mission.expiry.time_millis
        return int(time.time() * 1000)
