"""WorldState service / 世界状态服务层

负责 WorldState 数据的拉取、解析、缓存管理（JSON 文件持久化 + 后台自动刷新）
和翻译管道（节点名/物品名翻译）。

镜像 Java: WorldStateUtils.java
"""
from __future__ import annotations

import asyncio
import contextlib
import random
import re
import time
from pathlib import Path
from typing import Any

import orjson
from tortoise.exceptions import DoesNotExist

from astrbot.api import logger

from ..api.api import WF_WORLD_STATE
from ..init import init_ready
from ..model.export.night_wave import NightWave
from ..model.export.nodes import Nodes
from ..model.export.reward.reward_pool import RewardPool
from ..model.export.weapons import Weapons
from ..model.world_state import (
    ActiveMission,
    Alert,
    CambionCycle,
    CetusCycle,
    DailyDeals,
    DuvalierCycle,
    EarthCycle,
    EndlessXpCategory,
    Invasion,
    KnownCalendarSeasons,
    LiteSortie,
    SeasonInfo,
    Sortie,
    SteelPathOffering,
    SyndicateMission,
    VallisCycle,
    VoidStorms,
    VoidTrader,
    WorldState,
    ZarimanCycle,
)
from ..service.state_translation import StateTranslationService
from ..util import fetch_json
from ..util.data_path import get_public_data_path
from ..util.string_utils import get_last_three_segments, split_camel_case
from ..wenum.fissure_type import FissureTypeEnum

_MARKUP_RE = re.compile(r"<[^<>]*>")


def _strip_markup(text: str) -> str:
    """去掉物品名里的 ``<...>`` 标记 — 镜像 Java deleteBetweenAndMarkers。"""
    return _MARKUP_RE.sub("", text).strip()


class WorldStateService:
    """世界状态服务。

    提供对 Warframe 世界状态的访问，包含:
    - JSON 文件持久化缓存
    - 启动时缓存检查（未过期直接加载，过期则刷新）
    - 3 次重试机制（全部失败后停止自动请求）
    - 后台自动刷新循环
    - 翻译管道（节点名 + 物品路径 → 人类可读名称）
    """

    @classmethod
    async def _fetch_raw(cls) -> dict[str, Any] | None:
        """拉取原始 WorldState 数据。

        Returns:
            原始 JSON 字典，失败返回 None。
        """
        return await fetch_json(WF_WORLD_STATE)

    # ── 类变量 ──────────────────────────────────────────────────────────
    _cache: dict[str, Any] = {"ws": None}
    _refresh_task: asyncio.Task | None = None
    _failed: bool = False
    _MAX_RETRIES: int = 3
    _RETRY_DELAY: float = 5.0

    # ══════════════════════════════════════════════════════════════════
    # 缓存生命周期（镜像 Java WarframeCache + 计划 v2 状态机）
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def start_cache(cls) -> None:
        """启动缓存：优先从文件恢复，否则 API 拉取 + 启动后台刷新循环。

        在 main.py 的 _do_initialize() 末尾调用。
        内置可重入保护：重复调用不会创建僵尸后台任务。
        """
        if cls._refresh_task is not None and not cls._refresh_task.done():
            logger.warning("WorldState 缓存刷新任务已在运行，跳过重复启动")
            return

        cache_path = Path(get_public_data_path()) / "world_state_cache.json"

        if cache_path.exists():
            try:
                cached = orjson.loads(cache_path.read_bytes())
                if cached.get("min_expiry", 0) > time.time():
                    ws = WorldState.model_validate(cached["data"])
                    cls._cache["ws"] = ws
                    cls._failed = False
                    logger.info(
                        f"WorldState 从缓存文件加载成功，min_expiry={cached['min_expiry']}"
                    )
                    await cls._notify_build_label(ws)
                    cls._refresh_task = asyncio.create_task(cls._refresh_loop())
                    return
                else:
                    logger.info("WorldState 缓存文件已过期，重新拉取")
            except Exception as e:
                logger.warning(f"WorldState 缓存文件读取失败: {e}，删除损坏缓存并重新拉取")
                with contextlib.suppress(OSError):
                    cache_path.unlink(missing_ok=True)

        await cls._fetch_with_retry()
        cls._refresh_task = asyncio.create_task(cls._refresh_loop())

    @classmethod
    async def stop_cache(cls) -> None:
        """停止后台刷新循环。

        在 main.py 的 terminate() 中调用。
        """
        if cls._refresh_task and not cls._refresh_task.done():
            cls._refresh_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await cls._refresh_task
            cls._refresh_task = None
        logger.info("WorldState 缓存已停止")

    @classmethod
    async def force_refresh(cls) -> bool:
        """手动强制刷新缓存（重置失败状态后重试）。

        Returns:
            True 表示刷新成功。
        """
        cls._failed = False
        return await cls._fetch_with_retry()

    # ══════════════════════════════════════════════════════════════════
    # 内部：拉取 + 重试 + 文件持久化
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def _fetch_with_retry(cls) -> bool:
        """带重试的 WorldState 拉取（最多 3 次，间隔 5 秒）。

        Returns:
            True 表示拉取成功。
        """
        for attempt in range(1, cls._MAX_RETRIES + 1):
            try:
                ws, raw = await cls._fetch_and_parse()
                if ws and raw:
                    cls._cache["ws"] = ws
                    cls._save_to_file(ws)
                    cls._failed = False
                    logger.info(f"WorldState API 拉取成功 (第 {attempt} 次)")
                    await cls._notify_build_label(ws)
                    return True
            except Exception as e:
                logger.warning(
                    f"WorldState API 请求失败 ({attempt}/{cls._MAX_RETRIES}): {e}"
                )
            if attempt < cls._MAX_RETRIES:
                delay = cls._RETRY_DELAY * (2 ** (attempt - 1))
                delay += random.uniform(0, delay * 0.5)
                await asyncio.sleep(delay)

        cls._failed = True
        logger.error("WorldState API 全部重试失败，已停止自动请求")
        return False

    @classmethod
    async def _fetch_and_parse(cls) -> tuple[WorldState | None, dict | None]:
        """拉取原始 JSON 并解析为 WorldState 模型。

        Returns:
            (解析后的 WorldState 对象, 原始 JSON dict)，失败返回 (None, None)。
        """
        raw = await cls._fetch_raw()
        if raw is None:
            return None, None
        return WorldState.model_validate(raw), raw

    @classmethod
    def _save_to_file(cls, ws: WorldState) -> None:
        """将 WorldState 持久化到 JSON 缓存文件。

        使用 orjson + mode="json"（StrEnum 的 value 即 name 字符串，
        mode="json" 序列化输出 "VoidT4"/"FC_GRINEER" 而非 JSON 数组）。
        """
        cache_path = Path(get_public_data_path()) / "world_state_cache.json"
        min_expiry = cls._calc_min_expiry(ws)
        payload = {
            "cached_at": int(time.time()),
            "min_expiry": int(min_expiry / 1000),  # 毫秒 → 秒
            "data": ws.model_dump(by_alias=True, mode="json"),
        }
        cache_path.write_bytes(
            orjson.dumps(payload, option=orjson.OPT_INDENT_2)
        )

    @classmethod
    async def _refresh_loop(cls) -> None:
        """后台自动刷新循环：TTL-5 秒后自动拉取新数据。

        失败状态下不自动刷新，仅通过 force_refresh() 手动触发。
        """
        while True:
            if cls._failed:
                await asyncio.sleep(60)
                continue

            ws = cls._cache.get("ws")
            if ws is None:
                await asyncio.sleep(60)
                continue

            ttl = cls._calc_ttl(ws)
            await asyncio.sleep(max(1, ttl - 5))

            try:
                new_ws, new_raw = await cls._fetch_and_parse()
                if new_ws and new_raw:
                    cls._cache["ws"] = new_ws
                    cls._save_to_file(new_ws)
                    logger.debug("WorldState 后台刷新成功")
                    await cls._notify_build_label(new_ws)
            except Exception as e:
                logger.warning(f"WorldState 后台刷新失败: {e}")

    @classmethod
    async def _notify_build_label(cls, ws: WorldState) -> None:
        """把 BuildLabel 交给游戏版本跟踪：变化时触发导出数据刷新。"""
        label = getattr(ws, "build_label", None)
        if not label:
            return
        try:
            from ..init.game_version import on_build_label

            await on_build_label(label)
        except Exception as exc:  # 版本检测失败不能影响世界状态
            logger.debug(f"游戏版本检测失败: {exc}")

    @classmethod
    async def _get_cached(cls) -> WorldState | None:
        """获取缓存的 WorldState（等待初始化完成）。

        Returns:
            缓存的 WorldState 对象，未初始化返回 None。
        """
        await init_ready()
        return cls._cache.get("ws")

    # ══════════════════════════════════════════════════════════════════
    # TTL 计算
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    def _calc_min_expiry(cls, ws: WorldState) -> int:
        """计算所有子模型中最小的 expiry 时间戳（毫秒）。

        遍历所有含 expiry 字段的子模型列表，取最小值。
        无有效 expiry 时返回当前时间 + 5 分钟。
        """
        min_expiry = float("inf")
        sources: list[list[Any]] = [
            ws.alerts,
            ws.sorties,
            ws.active_missions,
            ws.invasions,
            ws.void_traders,
            ws.syndicate_missions,
            ws.daily_deals,
            ws.lite_sorties,
            ws.goals,
            ws.flash_sales,
            ws.prime_vault_traders,
            ws.void_storms,
        ]
        for model_list in sources:
            for m in model_list:
                if hasattr(m, "expiry") and m.expiry is not None:
                    min_expiry = min(min_expiry, m.expiry.time_millis)
        if min_expiry == float("inf"):
            return int(time.time() * 1000) + 300_000
        return int(min_expiry)

    @classmethod
    def _calc_ttl(cls, ws: WorldState) -> int:
        """计算缓存 TTL（秒），限制在 [30, 300] 区间。"""
        min_ms = cls._calc_min_expiry(ws)
        ttl = int((min_ms - time.time() * 1000) / 1000)
        return max(30, min(ttl, 300))

    # ══════════════════════════════════════════════════════════════════
    # 翻译管道（内部私有）
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def _translate_node(cls, node_key: str) -> str:
        """将节点 key 翻译为 "节点名(星系名)" 格式。

        镜像 Java: nodesRepository.findById(nodeKey) → name(systemName)
        """
        node = await cls.get_node(node_key)
        if node:
            if node.systemName:
                return f"{node.name}({node.systemName})"
            return node.name
        return node_key

    @classmethod
    async def _batch_translate_nodes(
        cls, node_keys: set[str],
    ) -> dict[str, str]:
        """批量翻译节点 key 为显示名称，避免 N+1 查询。

        Args:
            node_keys: 需要翻译的节点 key 集合。

        Returns:
            {node_key: display_name} 映射表。
        """
        if not node_keys:
            return {}
        db_nodes = await Nodes.filter(uniqueName__in=list(node_keys)).all()
        result: dict[str, str] = {}
        for n in db_nodes:
            if n.systemName:
                result[n.uniqueName] = f"{n.name}({n.systemName})"
            else:
                result[n.uniqueName] = n.name
        # 未找到的 key 保留原值
        return {k: result.get(k, k) for k in node_keys}

    @classmethod
    async def _batch_translate_items(cls, paths: set[str]) -> dict[str, str]:
        """批量翻译物品路径 → 中文名（通过 suffix 匹配）。

        镜像 Java: str.findByUniqueName(StringUtils.getLastThreeSegments(i))
        """
        if not paths:
            return {}

        # 提取 suffix 用于匹配
        suffix_map: dict[str, str] = {}
        for p in paths:
            seg = get_last_three_segments(p)
            if seg:
                suffix_map[seg] = p

        # 批量 suffix 匹配
        translated = await StateTranslationService.batch_translate_by_suffix(
            set(suffix_map.keys())
        )

        # 映射回原始路径
        return {suffix_map[k]: v for k, v in translated.items()}

    # ══════════════════════════════════════════════════════════════════
    # get_alerts() — 警报 → list[Alert]
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def get_alerts(cls) -> list[Alert]:
        """获取警报列表（翻译节点 + 物品名称，修改模型字段就地）。

        镜像 Java: getAlerts() → translateAlerts()

        Returns:
            Alert 模型列表，mission_info.location 已翻译为节点名，
            mission_info.mission_reward.items 已翻译为中文物品名。
        """
        ws = await cls._get_cached()
        if ws is None:
            return []

        # 收集所有需要翻译的物品路径
        all_item_paths: set[str] = set()
        valid_alerts: list[Alert] = []
        for a in ws.alerts:
            if a.mission_info is None:
                continue
            valid_alerts.append(a)
            reward = a.mission_info.mission_reward
            if reward and reward.counted_items:
                all_item_paths.update(item.name for item in reward.counted_items)

        # 批量翻译物品
        item_translations = await cls._batch_translate_items(all_item_paths)

        # 批量翻译节点名
        node_keys = {
            a.mission_info.location
            for a in valid_alerts
            if a.mission_info and a.mission_info.location
        }
        node_translations = await cls._batch_translate_nodes(node_keys)

        # 就地翻译节点名和物品名
        for a in valid_alerts:
            mi = a.mission_info
            if mi is None:
                continue

            # 翻译节点名 → 覆盖 location 字段
            if mi.location:
                mi.location = node_translations.get(mi.location, mi.location)

            # 翻译物品名 → 覆盖 counted_items 中 Item 的 name
            reward = mi.mission_reward
            if reward and reward.counted_items:
                for item in reward.counted_items:
                    item.name = item_translations.get(item.name, item.name)

        return valid_alerts

    # ══════════════════════════════════════════════════════════════════
    # get_sorties() — 突击 → list[Sortie]
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def get_sorties(cls) -> list[Sortie]:
        """获取突击列表（翻译 variants 节点名称，修改模型字段就地）。

        镜像 Java: getSorties()

        Returns:
            Sortie 模型列表，variants 中各 variant.node 已翻译为节点名。
        """
        ws = await cls._get_cached()
        if ws is None:
            return []

        # 批量翻译所有 variant 节点
        node_keys = {
            v.node
            for s in ws.sorties
            for v in s.variants
            if v.node
        }
        node_translations = await cls._batch_translate_nodes(node_keys)

        for s in ws.sorties:
            for v in s.variants:
                if v.node:
                    v.node = node_translations.get(v.node, v.node)

        return ws.sorties

    # ══════════════════════════════════════════════════════════════════
    # get_fissures() — 裂隙 → list[ActiveMission] | list[VoidStorms]
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def get_fissures(
        cls, fissure_type: FissureTypeEnum = FissureTypeEnum.ACTIVE_MISSION,
    ) -> list[ActiveMission]:
        """获取裂隙任务列表（翻译节点 + faction，按 modifier 排序）。

        镜像 Java: getFissure(FissureTypeEnum)

        Args:
            fissure_type: 裂隙查询类型
                - ACTIVE_MISSION: 普通裂隙（非钢铁之路）
                - STEEL_PATH: 钢铁之路裂隙
                - VOID_STORMS: 虚空风暴（Railjack 裂隙）

        Returns:
            list[ActiveMission]
            所有类型统一返回 ActiveMission，node/faction/mission_type 已从 Nodes 表覆盖。
        """
        ws = await cls._get_cached()
        if ws is None:
            return []

        if fissure_type == FissureTypeEnum.ACTIVE_MISSION:
            return await cls._translate_active_missions(
                [m for m in ws.active_missions if not m.hard]
            )
        elif fissure_type == FissureTypeEnum.STEEL_PATH:
            return await cls._translate_active_missions(
                [m for m in ws.active_missions if m.hard]
            )
        elif fissure_type == FissureTypeEnum.VOID_STORMS:
            return await cls._translate_void_storms(ws.void_storms)
        else:
            return []

    @classmethod
    async def _translate_active_missions(
        cls, missions: list[ActiveMission],
    ) -> list[ActiveMission]:
        """翻译 ActiveMission 列表（节点 + faction 从 Nodes 表取）。

        批量查询 Nodes 表避免 N+1 问题。
        """
        if not missions:
            return []

        node_names = {m.node for m in missions if m.node}
        if node_names:
            db_nodes = await Nodes.filter(uniqueName__in=list(node_names)).all()
            node_map = {n.uniqueName: n for n in db_nodes}
        else:
            node_map = {}

        for m in missions:
            if m.node and m.node in node_map:
                node = node_map[m.node]
                if node.systemName:
                    m.node = f"{node.name}({node.systemName})"
                else:
                    m.node = node.name
                m.faction = node.faction
                m.mission_type = node.mission_type

        # 按 modifier 排序
        return sorted(missions, key=lambda m: m.modifier.name if m.modifier else "")

    @classmethod
    async def _translate_void_storms(
        cls, void_storms: list[VoidStorms],
    ) -> list[ActiveMission]:
        """转换 VoidStorms → ActiveMission（节点 + faction + mission_type 从 Nodes 表补全）。

        镜像 Java: getFissure(VOID_STORMS) 分支。
        批量查询 Nodes 表避免 N+1 问题。
        """
        if not void_storms:
            return []

        node_names = {vs.node for vs in void_storms if vs.node}
        if node_names:
            db_nodes = await Nodes.filter(uniqueName__in=list(node_names)).all()
            node_map = {n.uniqueName: n for n in db_nodes}
        else:
            node_map = {}

        result: list[ActiveMission] = []
        for vs in void_storms:
            am = ActiveMission()
            am.activation = vs.activation
            am.expiry = vs.expiry
            am.modifier = vs.tier  # tier → modifier
            am.void_storms = True

            if vs.node and vs.node in node_map:
                node = node_map[vs.node]
                am.node = f"{node.name}({node.systemName})" if node.systemName else node.name
                am.faction = node.faction  # 从 Nodes 表补全
                am.mission_type = node.mission_type  # 从 Nodes 表补全
            else:
                am.node = vs.node

            result.append(am)
        return sorted(result, key=lambda m: m.modifier.name if m.modifier else "")

    # ══════════════════════════════════════════════════════════════════
    # get_invasions() — 入侵 → list[Invasion]
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def get_invasions(cls) -> list[Invasion]:
        """获取入侵列表（过滤 completed=true，翻译节点 + countedItems）。

        镜像 Java: getInvasions() → translateInvasion()

        Returns:
            Invasion 模型列表，node 已翻译为节点名，
            counted_items 的 name 已翻译为中文物品名。
        """
        ws = await cls._get_cached()
        if ws is None:
            return []

        # 收集所有需要翻译的物品路径
        all_item_paths: set[str] = set()
        valid_invasions: list[Invasion] = []
        for inv in ws.invasions:
            if inv.completed:
                continue
            valid_invasions.append(inv)
            # 防守方奖励
            if inv.defender_reward and inv.defender_reward.counted_items:
                for ci in inv.defender_reward.counted_items:
                    all_item_paths.add(ci.name)
            # 进攻方奖励（可能是多个）
            for ar in inv.attacker_reward:
                if ar.counted_items:
                    for ci in ar.counted_items:
                        all_item_paths.add(ci.name)

        # 批量翻译物品
        item_translations = await cls._batch_translate_items(all_item_paths)

        # 批量翻译节点名
        node_keys = {inv.node for inv in valid_invasions if inv.node}
        node_translations = await cls._batch_translate_nodes(node_keys)

        # 就地翻译
        for inv in valid_invasions:
            # 翻译节点名 → 覆盖 node 字段
            if inv.node:
                inv.node = node_translations.get(inv.node, inv.node)

            # 翻译防守方奖励物品名
            if inv.defender_reward and inv.defender_reward.counted_items:
                for ci in inv.defender_reward.counted_items:
                    ci.name = item_translations.get(ci.name, ci.name)

            # 翻译进攻方奖励物品名
            for ar in inv.attacker_reward:
                if ar.counted_items:
                    for ci in ar.counted_items:
                        ci.name = item_translations.get(ci.name, ci.name)

        return valid_invasions

    # ══════════════════════════════════════════════════════════════════
    # get_void_trader() — 虚空商人 → VoidTrader | None
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def get_void_trader(cls) -> VoidTrader | None:
        """获取虚空商人数据（翻译节点 + manifest 物品名，修改模型字段就地）。

        镜像 Java: getVoidTraders() → translateVoidTraders()

        Returns:
            VoidTrader 模型（node 已翻译，manifest 各 item 已翻译），
            若无数据返回 None。
        """
        ws = await cls._get_cached()
        if ws is None:
            return None

        if not ws.void_traders:
            return None

        vt = ws.void_traders[0]

        # 翻译节点名 → 覆盖 node 字段
        if vt.node:
            vt.node = await cls._translate_node(vt.node)

        # 收集并翻译 manifest 物品
        manifest_paths: set[str] = set()
        for m_item in vt.manifest:
            if m_item.item:
                manifest_paths.add(m_item.item)
        item_translations = await cls._batch_translate_items(manifest_paths)

        # 就地翻译 manifest 物品名
        for m_item in vt.manifest:
            if m_item.item:
                m_item.item = item_translations.get(m_item.item, m_item.item)

        return vt

    # ══════════════════════════════════════════════════════════════════
    # get_daily_deals() — 每日特惠 → list[DailyDeals]
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def get_daily_deals(cls) -> list[DailyDeals]:
        """获取每日特惠列表（翻译物品名称，修改模型字段就地）。

        镜像 Java: getDailyDeals() → translateDailyDeals()

        Returns:
            DailyDeals 模型列表，item 字段已翻译为中文物品名。
        """
        ws = await cls._get_cached()
        if ws is None:
            return []

        # 收集所有物品路径
        item_paths: set[str] = set()
        for d in ws.daily_deals:
            if d.item:
                item_paths.add(d.item)
        item_translations = await cls._batch_translate_items(item_paths)

        # 就地翻译物品名
        for d in ws.daily_deals:
            if d.item:
                d.item = item_translations.get(d.item, d.item)

        return ws.daily_deals

    # ══════════════════════════════════════════════════════════════════
    # get_lite_sortie() — 执刑官猎杀 → list[LiteSortie]
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def get_lite_sortie(cls) -> list[LiteSortie]:
        """获取执刑官猎杀列表（翻译 missions 节点名称，修改模型字段就地）。

        镜像 Java: getLiteSortie()

        Returns:
            LiteSortie 模型列表，missions 中各 mission.node 已翻译为节点名。
        """
        ws = await cls._get_cached()
        if ws is None:
            return []

        # 批量翻译所有 mission 节点
        node_keys = {
            m.node
            for ls in ws.lite_sorties
            for m in ls.missions
            if m.node
        }
        node_translations = await cls._batch_translate_nodes(node_keys)

        for ls in ws.lite_sorties:
            for m in ls.missions:
                if m.node:
                    m.node = node_translations.get(m.node, m.node)

        return ws.lite_sorties

    # ══════════════════════════════════════════════════════════════════
    # get_season_info() — 赛季信息 → SeasonInfo | None
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def get_season_info(cls) -> SeasonInfo | None:
        """获取午夜电波赛季信息（挑战信息从 NightWave 表查询，修改模型字段就地）。

        镜像 Java: getSeasonInfo()

        Returns:
            SeasonInfo 模型（active_challenges 已从 NightWave 表填充中文名/描述），
            若无数据返回 None。
        """
        ws = await cls._get_cached()
        if ws is None:
            return None

        si = ws.season_info
        if si is None:
            return None

        # 批量查询挑战信息避免 N+1（从 NightWave 表查询后覆盖字段）
        if si.active_challenges:
            challenge_ids = [ac.challenge for ac in si.active_challenges]
            db_challenges = await NightWave.filter(
                uniqueName__in=challenge_ids
            ).all()
            nw_map = {nw.uniqueName: nw for nw in db_challenges}

            for ac in si.active_challenges:
                nw = nw_map.get(ac.challenge)
                if nw is not None:
                    ac.name = nw.name
                    ac.description = nw.get_description()
                    ac.standing = nw.standing
                    ac.required = nw.required
                    ac.daily = nw.is_daily_tasks
                    ac.weekly = nw.is_weekly_tasks
                    ac.elite = nw.is_elite_missions
        return si

    # ══════════════════════════════════════════════════════════════════
    # get_duviri_cycle() — 双衍王境 → DuvalierCycle | None
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def get_duviri_cycle(cls) -> DuvalierCycle | None:
        """获取双衍王境周期（EXC_HARD 武器名翻译，修改 choices 列表就地）。

        镜像 Java: getDuvalierCycle() → translateDuvalierCycle()

        Returns:
            DuvalierCycle 模型（EXC_HARD choices 已翻译为中文武器名）。
        """
        ws = await cls._get_cached()
        if ws is None:
            return None

        cycle: DuvalierCycle = ws.duvalier_cycle

        # 批量翻译 EXC_HARD choices 中的武器名（避免 N+1 查询）
        if cycle.choices:
            # 收集所有需要翻译的武器英文名
            all_weapon_names: set[str] = set()
            for c in cycle.choices:
                if c.category == EndlessXpCategory.EXC_HARD:
                    all_weapon_names.update(split_camel_case(s) for s in c.choices)

            # 批量查询 Weapons 表
            weapon_map: dict[str, str] = {}
            if all_weapon_names:
                db_weapons = await Weapons.filter(
                    englishName__in=list(all_weapon_names)
                ).all()
                weapon_map = {w.englishName: w.name for w in db_weapons if w.name}

            # 就地翻译
            for c in cycle.choices:
                if c.category == EndlessXpCategory.EXC_HARD:
                    c.choices = [
                        weapon_map.get(split_camel_case(s), split_camel_case(s))
                        for s in c.choices
                    ]

        return cycle

    # ══════════════════════════════════════════════════════════════════
    # get_earth_cycle() — 地球昼夜循环 → EarthCycle | None
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def get_earth_cycle(cls) -> EarthCycle | None:
        """获取地球昼夜循环。

        镜像 Java: getAllCycle() → EarthCycle

        Returns:
            EarthCycle 模型（纯计算，无需翻译）。
        """
        ws = await cls._get_cached()
        if ws is None:
            return None

        return ws.earth_cycle

    # ══════════════════════════════════════════════════════════════════
    # get_cetus_cycle() — 希图斯周期 → CetusCycle | None
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def get_cetus_cycle(cls) -> CetusCycle | None:
        """获取希图斯（夜灵平原）昼夜周期。

        镜像 Java: getAllCycle() → CetusCycle

        Returns:
            CetusCycle 模型（纯计算，无需翻译）。
        """
        ws = await cls._get_cached()
        if ws is None:
            return None

        return ws.cetus_cycle

    # ══════════════════════════════════════════════════════════════════
    # get_vallis_cycle() — 奥布山谷冷暖循环 → VallisCycle | None
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def get_vallis_cycle(cls) -> VallisCycle | None:
        """获取奥布山谷（金星）冷暖循环。

        镜像 Java: getAllCycle() → VallisCycle

        Returns:
            VallisCycle 模型（纯计算，无需翻译）。
        """
        ws = await cls._get_cached()
        if ws is None:
            return None

        return ws.vallis_cycle

    # ══════════════════════════════════════════════════════════════════
    # get_zariman_cycle() — 扎里曼轮换 → ZarimanCycle | None
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def get_zariman_cycle(cls) -> ZarimanCycle | None:
        """获取扎里曼号轮换循环。

        镜像 Java: getAllCycle() → ZarimanCycle

        Returns:
            ZarimanCycle 模型（纯计算，无需翻译）。
        """
        ws = await cls._get_cached()
        if ws is None:
            return None

        return ws.zariman_cycle

    # ══════════════════════════════════════════════════════════════════
    # get_cambion_cycle() — 魔胎之境循环 → CambionCycle | None
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def get_cambion_cycle(cls) -> CambionCycle | None:
        """获取魔胎之境（火卫二）Fass/Vome 循环。

        镜像 Java: getAllCycle() → CambionCycle

        Returns:
            CambionCycle 模型（纯计算，无需翻译）。
        """
        ws = await cls._get_cached()
        if ws is None:
            return None

        return ws.cambion_cycle

    # ══════════════════════════════════════════════════════════════════
    # get_steel_path() — 钢铁之路 → SteelPathOffering | None
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def get_steel_path(cls) -> SteelPathOffering | None:
        """获取钢铁之路献礼数据。

        镜像 Java: WarframeCache.getWarframeStatus().getSteelPath()

        Returns:
            SteelPathOffering 模型（纯计算，无需翻译）。
        """
        ws = await cls._get_cached()
        if ws is None:
            return None

        return ws.steel_path

    # ══════════════════════════════════════════════════════════════════
    # get_syndicate_mission() — 集团赏金任务
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def get_syndicate_mission(
        cls, syndicate_tag,
    ) -> SyndicateMission | None:
        """获取指定集团的赏金任务（筛选 jobs 非空的条目，翻译 job 类型）。

        镜像 Java: SyndicateMissionsUtils.getSyndicateMissions()

        Args:
            syndicate_tag: SyndicateEnum 成员（如 SyndicateEnum.CetusSyndicate）。

        Returns:
            SyndicateMission 模型（jobs 非空且已翻译），无匹配返回 None。
        """
        ws = await cls._get_cached()
        if ws is None:
            return None

        for sm in ws.syndicate_missions:
            if sm.tag is syndicate_tag and sm.jobs:
                # 批量收集 type_keys 与 reward_keys（融合为一次遍历）
                type_keys: set[str] = set()
                reward_keys: set[str] = set()
                for job in sm.jobs:
                    if key := (job.type or job.location_tag):
                        type_keys.add(key)
                    if job.rewards:
                        reward_keys.add(job.rewards)

                # 批量翻译 job 类型
                if type_keys:
                    type_map = await cls._batch_translate_job_types(type_keys)
                    for job in sm.jobs:
                        if key := (job.type or job.location_tag):
                            translated = type_map.get(key)
                            if translated:
                                job.type = translated

                # 批量查询奖励池数据并翻译物品名
                if reward_keys:
                    pool_map = await cls._batch_lookup_reward_pools(reward_keys)
                    await cls._batch_translate_reward_items(pool_map)
                    for job in sm.jobs:
                        if job.rewards and (rp := pool_map.get(job.rewards)):
                            job.reward_pool = rp

                return sm

        return None

    @classmethod
    async def _translate_job_type(cls, type_key: str) -> str | None:
        """翻译赏金任务类型（从 StateTranslation 表查询，回退到 Nodes 表）。"""
        if not type_key:
            return None
        with contextlib.suppress(Exception):
            key = get_last_three_segments(type_key)
            if key:
                trans = await StateTranslationService.get_state_translation(key)
                if trans:
                    return trans
        return None

    @classmethod
    async def _batch_translate_job_types(
        cls, type_keys: set[str],
    ) -> dict[str, str]:
        """批量翻译赏金任务类型（单次查询，消除 N+1）。"""
        result: dict[str, str] = {}
        if not type_keys:
            return result
        # 构建原始 key → 查询 key 的映射
        mapping: dict[str, str] = {}
        query_keys: set[str] = set()
        for tk in type_keys:
            if qk := get_last_three_segments(tk):
                mapping[tk] = qk
                query_keys.add(qk)
        if not query_keys:
            return result
        # 批量查询 StateTranslation
        translations = await StateTranslationService.batch_translate_by_suffix(query_keys)
        for tk, qk in mapping.items():
            if translated := translations.get(qk):
                result[tk] = translated
        return result

    @classmethod
    async def _batch_lookup_reward_pools(
        cls, reward_keys: set[str],
    ) -> dict[str, dict]:
        """批量查询 RewardPool 表，构建 renderer 所需的 reward_pool dict。"""
        if not reward_keys:
            return {}

        pools = await RewardPool.filter(
            uniqueName__in=list(reward_keys)
        ).prefetch_related("rewards")

        return {
            pool.uniqueName: {
                "rewards": [
                    {
                        "item": r.get_item(),
                        "itemCount": r.itemCount if r.itemCount is not None else 1,
                        "rarity": r.rarity or "COMMON",
                    }
                    for r in pool.rewards
                ],
            }
            for pool in pools
        }

    @classmethod
    async def _batch_translate_reward_items(
        cls, pool_map: dict[str, dict],
    ) -> None:
        """原地翻译 reward_pool dict 中 item 的 /Lotus/ 路径。"""
        if not pool_map:
            return

        lotus_map: dict[str, str] = {}
        for pool_data in pool_map.values():
            for entry in pool_data.get("rewards", []):
                item = entry.get("item", "")
                if item.startswith("/Lotus/"):
                    seg = get_last_three_segments(item)
                    if seg:
                        lotus_map[item] = seg

        if not lotus_map:
            return

        translations = await StateTranslationService.batch_translate_by_suffix(
            set(lotus_map.values())
        )

        for pool_data in pool_map.values():
            for entry in pool_data.get("rewards", []):
                item = entry.get("item", "")
                if item.startswith("/Lotus/"):
                    seg = lotus_map.get(item)
                    if seg and seg in translations:
                        entry["item"] = translations[seg]

    # ══════════════════════════════════════════════════════════════════
    # get_known_calendar_seasons() — 1999日历
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def get_known_calendar_seasons(cls) -> list[KnownCalendarSeasons]:
        """获取1999日历季节数据（day-of-year 拆月 + 事件翻译）。

        镜像 Java: getKnownCalendarSeasons() → processSeason()

        Returns:
            KnownCalendarSeasons 模型列表，``month_days`` 已按月分组。
        """
        ws = await cls._get_cached()
        if ws is None:
            return []

        calendars = ws.known_calendar_seasons
        for calendar in calendars:
            calendar.process_days()
        await cls._translate_calendar_events(calendars)
        return calendars

    @classmethod
    async def _translate_calendar_events(
        cls,
        calendars: list[KnownCalendarSeasons],
    ) -> None:
        """翻译日历事件里的 challenge/reward/upgrade 路径。

        镜像 Java processEvent()：按 uniqueName 后缀查 StateTranslation，
        查不到就保留原始路径（与 Java 的 ifPresent 行为一致）。
        """
        paths: set[str] = set()
        for calendar in calendars:
            for day in calendar.days:
                for evt in day.events:
                    for value in (evt.challenge, evt.reward, evt.upgrade):
                        if value and value.startswith("/"):
                            paths.add(value)
        if not paths:
            return

        translations = await cls._batch_translate_items(paths)
        if not translations:
            return

        for calendar in calendars:
            for day in calendar.days:
                for evt in day.events:
                    if evt.challenge in translations:
                        evt.challenge = translations[evt.challenge]
                    if evt.reward in translations:
                        evt.reward = _strip_markup(translations[evt.reward])
                    if evt.upgrade in translations:
                        evt.upgrade = translations[evt.upgrade]

    # ══════════════════════════════════════════════════════════════════
    # 星图节点查询（保留原有方法）
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def get_node_by_name(cls, name: str) -> Nodes | None:
        """根据节点名称查找星图节点。"""
        try:
            return await Nodes.get(name=name)
        except DoesNotExist:
            return None

    @classmethod
    async def get_node(cls, unique_name: str) -> Nodes | None:
        """根据唯一标识查找星图节点。"""
        try:
            return await Nodes.get(uniqueName=unique_name)
        except DoesNotExist:
            return None

    @classmethod
    def clear_cache(cls) -> None:
        """清除内存中的 WorldState 缓存（不清除文件缓存）。"""
        cls._cache["ws"] = None
