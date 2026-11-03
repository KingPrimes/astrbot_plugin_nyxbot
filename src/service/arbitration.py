"""Arbitration service / 仲裁服务

对齐 Go: ``internal/warframe/arbitration.go`` + ``arbitration_tier.go``。

- 数据源：``https://browse.wf/arbys.txt``，逐行 ``unix秒,节点ID``。
- 缓存：内存快照 + 插件数据目录下的 ``arbys.txt``；消费路径只读本地文件，不触网。
- 窗口：仅保留 ``expiry > now`` 且 ``activation < now + 30d`` 的条目；快照超过
  1 小时后重新解析本地文件，让 30 天窗口随时间前滚。
- 前瞻列表：按 ``arbitration_tier`` 表分级，仅保留 S/A/B，最多 10 条。
"""
from __future__ import annotations

import asyncio
import contextlib
import time
from pathlib import Path

from aiohttp import ClientTimeout
from tortoise.transactions import in_transaction

from astrbot.api import logger

from ..api import CdnClient
from ..model.arbitration import Arbitration, ArbitrationView
from ..model.arbitration_tier import ArbitrationTier
from ..model.export.nodes import Nodes
from ..util import fetch_text, get_plugin_version, get_public_data_path
from ..wenum.faction import FactionEnum

ARBITRATION_URL = "https://browse.wf/arbys.txt"
"""仲裁原始数据地址（browse.wf 官方导出，纯文本逐行 ``unix秒,节点ID``）。"""

ARBITRATION_DURATION = 3600
"""单场仲裁时长（秒，官方排期间隔恒为 3600）。"""

ARBITRATION_WINDOW = 30 * 24 * 3600
"""前瞻窗口：activation 距今 30 天内。"""

ARBITRATION_LIST_LIMIT = 10
"""仲裁前瞻列表最多返回条数。"""

_TIER_RANKS = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1, "F": 0}
_WORTH_TIER_THRESHOLD = "B"
_FETCH_RETRY_COUNT = 2
_FETCH_TIMEOUT = ClientTimeout(total=8)
"""单次拉取超时。browse.wf 在国内直连常超时，15s×3 会让启动尾部拖到 45s+。"""

_STARTUP_REFRESH_DELAY = 60.0
"""有本地缓存时，延迟多久再后台刷新（秒），避免启动瞬间抢带宽。"""

_REMOTE_REFRESH_INTERVAL = 12 * 3600.0
"""arbys.txt 远程刷新间隔（秒）。

文件覆盖的是 30 天滚动窗口（实测 721 条 / 约 1 MB），排期变化很慢，
半天拉一次足够；需要立刻更新用 ``/更新仲裁``。
"""

def _format_age(seconds: float) -> str:
    """把缓存年龄格式化成人类可读文本。"""
    if seconds < 3600:
        return f"{seconds / 60:.0f} 分钟"
    if seconds < 86400:
        return f"{seconds / 3600:.1f} 小时"
    return f"{seconds / 86400:.1f} 天"


class ArbitrationService:
    """仲裁缓存与查询服务（对齐 Go ArbitrationCache）。"""

    _data: list[Arbitration] = []
    _scanned_at: float = 0.0
    _rescan_interval: float = 3600.0
    """内存快照重新解析本地文件的间隔（秒）。

    只涉及本地文件解析（约 1 MB 文本），不触网，与远程刷新间隔
    ``_REMOTE_REFRESH_INTERVAL`` 是两件事。
    """
    _state_lock: asyncio.Lock | None = None
    _reload_lock: asyncio.Lock | None = None
    _bootstrap_task: asyncio.Task | None = None
    _refresh_task: asyncio.Task | None = None

    # ══════════════════════════════════════════════════════════════════
    # 生命周期 / Lifecycle
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    def start(cls, *, allow_network: bool = True) -> None:
        """启动后台预热：拉取 arbys.txt + 同步仲裁分级（不阻塞主流程）。

        Args:
            allow_network: 是否允许联网刷新。``never``/``offline`` 模式传 False，
                此时只用本地缓存，不产生任何远程请求。
        """
        if cls._bootstrap_task and not cls._bootstrap_task.done():
            return
        cls._bootstrap_task = asyncio.create_task(
            cls._bootstrap(allow_network=allow_network)
        )

    @classmethod
    async def stop(cls) -> None:
        """停止后台预热任务。"""
        for attr in ("_bootstrap_task", "_refresh_task"):
            task = getattr(cls, attr)
            setattr(cls, attr, None)
            if task and not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    @classmethod
    async def _bootstrap(cls, *, allow_network: bool = True) -> None:
        """启动预热：本地缓存优先，缓存新鲜或不允许联网时完全不触网。

        browse.wf 在国内直连经常超时，启动时强制联网会把"初始化完成"拖到 50 秒以上。
        本地 ``arbys.txt`` 在 ``_REMOTE_REFRESH_INTERVAL``（12 小时）内视为新鲜，
        直接用、不刷新；过期才在 ``_STARTUP_REFRESH_DELAY`` 秒后后台静默刷新。
        """
        cached = await cls._load()
        if cached:
            age = cls._cache_age_seconds()
            fresh = age is not None and age < _REMOTE_REFRESH_INTERVAL
            if not allow_network:
                logger.info(
                    f"仲裁数据使用本地缓存，共 {len(cached)} 条（当前模式不联网刷新）"
                )
            elif fresh:
                logger.info(
                    f"仲裁数据使用本地缓存，共 {len(cached)} 条"
                    f"（缓存 {_format_age(age)}前刷新，跳过远程拉取）"
                )
            else:
                logger.info(
                    f"仲裁数据使用本地缓存，共 {len(cached)} 条；"
                    f"{_STARTUP_REFRESH_DELAY:.0f} 秒后后台刷新"
                )
                cls._schedule_background_refresh()
            await cls._sync_tiers_if_needed(allow_network)
            return

        if not allow_network:
            logger.warning(
                "没有可用的仲裁缓存，且当前模式禁止联网刷新，/仲裁 将无数据"
            )
            return

        result = await asyncio.gather(cls.reload(), return_exceptions=True)
        if isinstance(result[0], BaseException):
            logger.warning(f"仲裁初始化 arbitration 失败: {result[0]}")
        await cls._sync_tiers_if_needed(allow_network)

    @classmethod
    async def _sync_tiers_if_needed(cls, allow_network: bool) -> None:
        """分级表为空时兜底同步一次。

        常规的版本驱动更新由 ``bootstrap`` 负责（只在 ``arbitration_tiers.json``
        随 DataSource 新版本变化时导入）；这里只兜住「表从来没填过」的情况，
        表里有数据就完全不联网。
        """
        if not allow_network:
            return
        try:
            if await ArbitrationTier.all().count() > 0:
                return
        except Exception as exc:  # 表不存在等情况交给 sync_tiers 兜底
            logger.debug(f"查询仲裁分级表失败: {exc}")
        logger.info("仲裁分级表为空，执行一次兜底同步")
        await asyncio.gather(cls.sync_tiers(), return_exceptions=True)

    @classmethod
    def _cache_age_seconds(cls) -> float | None:
        """本地 arbys.txt 距上次成功拉取的秒数；文件缺失返回 None。"""
        try:
            return time.time() - cls._cache_path().stat().st_mtime
        except OSError:
            return None

    @classmethod
    def _schedule_background_refresh(cls) -> None:
        """延迟后台刷新一次远程快照（失败只告警，不影响运行）。"""
        if cls._refresh_task and not cls._refresh_task.done():
            return

        async def _later() -> None:
            await asyncio.sleep(_STARTUP_REFRESH_DELAY)
            with contextlib.suppress(Exception):
                await cls.reload()

        cls._refresh_task = asyncio.create_task(_later())

    # ══════════════════════════════════════════════════════════════════
    # 远程拉取 + 本地缓存 / Fetch + local cache
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def reload(cls) -> bool:
        """强制重拉 arbys.txt：拉取 → 覆写本地文件 → 刷新内存快照。

        Returns:
            True 表示刷新成功。
        """
        async with cls._get_reload_lock():
            raw = await cls._fetch_arbys()
            if not raw:
                logger.warning("arbys.txt 拉取失败，保留原有缓存")
                return False

            entries = cls.parse_arbys(raw)
            if not entries:
                logger.warning("arbys.txt 在 30 天窗口内没有条目，拒绝覆写本地缓存")
                return False

            try:
                await cls._write_local_file(raw)
            except OSError as exc:
                logger.warning(f"arbys.txt 写入本地失败: {exc}")
                return False

            async with cls._get_state_lock():
                cls._data = entries
                cls._scanned_at = time.monotonic()
            logger.info(f"仲裁数据刷新完成，窗口内 {len(entries)} 条")
            return True

    @classmethod
    async def _fetch_arbys(cls) -> str | None:
        """从 browse.wf 拉取原文；失败重试 3 次。"""
        version = get_plugin_version().removeprefix("v") or "dev"
        headers = {"User-Agent": f"NyxBot/{version}"}
        for attempt in range(1, _FETCH_RETRY_COUNT + 1):
            raw = await fetch_text(
                ARBITRATION_URL,
                headers=headers,
                timeout=_FETCH_TIMEOUT,
            )
            if raw:
                return raw
            if attempt < _FETCH_RETRY_COUNT:
                await asyncio.sleep(1.5 * attempt)
        return None

    @classmethod
    def parse_arbys(cls, raw: str) -> list[Arbitration]:
        """解析 arbys.txt 原文，边解析边按 30 天窗口裁剪。

        畸形行（空行、缺列、时间戳非数字、节点为空）直接跳过；
        已过期与超出前瞻窗口的条目不入结果。
        """
        now = int(time.time())
        cutoff = now + ARBITRATION_WINDOW
        results: list[Arbitration] = []

        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            timestamp_text, separator, node_key = line.partition(",")
            if not separator:
                continue
            node_key = node_key.strip()
            if not node_key:
                continue
            try:
                activation = int(timestamp_text.strip())
            except ValueError:
                continue

            expiry = activation + ARBITRATION_DURATION
            if expiry <= now or activation >= cutoff:
                continue
            results.append(
                Arbitration(
                    activation=activation,
                    node_key=node_key,
                    expiry=expiry,
                )
            )
        return results

    @classmethod
    async def _load(cls) -> list[Arbitration]:
        """读取快照：内存 → 本地文件 → 空列表，全程不触网。"""
        async with cls._get_state_lock():
            fresh = (
                cls._data
                and time.monotonic() - cls._scanned_at < cls._rescan_interval
            )
            if fresh:
                return cls._data

            entries = await cls._read_local_file()
            if entries:
                cls._data = entries
                cls._scanned_at = time.monotonic()
                logger.debug(f"仲裁数据从本地文件重解析: {len(entries)} 条")
                return cls._data

            cls._scanned_at = time.monotonic()
            if not cls._data:
                logger.warning("没有可用的仲裁数据（本地文件缺失或超出窗口）")
            return cls._data

    @classmethod
    async def _read_local_file(cls) -> list[Arbitration]:
        """读取并解析本地 arbys.txt；文件缺失或窗口内无数据时返回空列表。"""
        path = cls._cache_path()
        try:
            raw = await asyncio.to_thread(path.read_text, encoding="utf-8")
        except FileNotFoundError:
            return []
        except (OSError, UnicodeError) as exc:
            logger.warning(f"读取 {path} 失败: {exc}")
            return []
        return cls.parse_arbys(raw)

    @classmethod
    async def _write_local_file(cls, raw: str) -> None:
        """原子写入本地缓存：先写 .tmp 再改名。"""
        path = cls._cache_path()
        tmp = path.with_name(path.name + ".tmp")

        def _write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(raw, encoding="utf-8")
            tmp.replace(path)

        await asyncio.to_thread(_write)

    @staticmethod
    def _cache_path() -> Path:
        """本地缓存路径（插件数据目录下 arbys.txt）。"""
        return Path(get_public_data_path()) / "arbys.txt"




    # ══════════════════════════════════════════════════════════════════
    # 查询 / Queries
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def get_arbitration(cls) -> Arbitration | None:
        """返回当前正在进行的仲裁（最近到期的一条）。

        必须同时满足 ``activation <= now < expiry``：只看 ``expiry > now`` 会把
        排期空档期里「还没开始」的下一场当成当前仲裁。
        """
        entries = await cls._load()
        now = int(time.time())
        active = [
            entry for entry in entries if entry.activation <= now < entry.expiry
        ]
        return min(active, key=lambda entry: entry.expiry) if active else None

    @classmethod
    async def get_arbitration_list(cls) -> list[Arbitration]:
        """返回值得参与的未来仲裁（S/A/B，最多 10 条）。"""
        entries = await cls._load()
        if not entries:
            return []

        tiers = await cls._load_tiers({entry.node_key for entry in entries})
        now = int(time.time())
        results: list[Arbitration] = []
        for entry in entries:
            if not cls.is_worth_tier(tiers.get(entry.node_key, "F")):
                continue
            if entry.activation > now:
                results.append(entry)
            if len(results) >= ARBITRATION_LIST_LIMIT:
                break
        return results

    @classmethod
    async def to_views(
        cls,
        entries: list[Arbitration],
    ) -> list[ArbitrationView]:
        """把仲裁条目转换为绘图 DTO（补节点名/任务类型/派系/评级）。"""
        if not entries:
            return []

        node_keys = {entry.node_key for entry in entries}
        node_map: dict[str, Nodes] = {}
        try:
            nodes = await Nodes.filter(uniqueName__in=list(node_keys)).all()
            node_map = {node.uniqueName: node for node in nodes}
        except Exception as exc:
            logger.warning(f"查询仲裁节点失败，回退节点 ID: {exc}")

        tiers = await cls._load_tiers(node_keys)
        views: list[ArbitrationView] = []
        for entry in entries:
            node = node_map.get(entry.node_key)
            if node is None:
                node_name = entry.node_key
                mission_name = ""
                faction = FactionEnum.FC_NONE
            else:
                node_name = (
                    f"{node.name}({node.systemName})"
                    if node.systemName
                    else node.name
                )
                mission_name = node.mission_type.display_name
                faction = node.faction

            views.append(
                ArbitrationView(
                    activation=entry.activation_dt,
                    expiry=entry.expiry_dt,
                    node=node_name,
                    mission_name=mission_name,
                    faction=faction,
                    tier=cls.normalize_tier(tiers.get(entry.node_key, "F")),
                )
            )
        return views

    @classmethod
    async def _load_tiers(cls, node_keys: set[str]) -> dict[str, str]:
        """批量查询节点评级；表不存在/数据库不可用时返回空映射。"""
        if not node_keys:
            return {}
        try:
            rows = await ArbitrationTier.filter(
                key__in=list(node_keys)
            ).values_list("key", "tier")
        except Exception as exc:
            logger.warning(f"查询仲裁分级失败，按 F 处理: {exc}")
            return {}
        return {key: cls.normalize_tier(tier) for key, tier in rows}

    # ══════════════════════════════════════════════════════════════════
    # 分级 / Tiers
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def normalize_tier(tier: str | None) -> str:
        """规整评级文本：去空白、转大写；未知值回退 ``F``。"""
        normalized = str(tier or "").strip().upper()
        return normalized if normalized in _TIER_RANKS else "F"

    @classmethod
    def is_worth_tier(cls, tier: str | None) -> bool:
        """评级是否达到值得参与阈值（S/A/B）。"""
        return _TIER_RANKS[cls.normalize_tier(tier)] >= _TIER_RANKS[
            _WORTH_TIER_THRESHOLD
        ]

    @classmethod
    async def sync_tiers(cls) -> int:
        """从 CDN 重拉 ``arbitration_tiers.json`` 并入库。

        先删除本次快照未包含的行，再写入/覆盖，使表内容与 CDN 严格一致。

        Returns:
            本次处理的记录数；失败返回 0。
        """
        data = await CdnClient.fetch_arbitration_tiers()
        if not data:
            logger.warning("仲裁分级数据为空，跳过同步")
            return 0

        records: dict[str, str] = {}
        for item in data:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or "").strip()
            if not key:
                continue
            records[key] = cls.normalize_tier(item.get("tier"))
        if not records:
            logger.warning("仲裁分级没有可用记录，跳过同步")
            return 0

        from ..init.engine import get_engine

        await get_engine()
        keys = list(records)
        async with in_transaction():
            existing = {row.key: row for row in await ArbitrationTier.all()}
            stale = set(existing) - set(keys)
            if stale:
                await ArbitrationTier.filter(key__in=list(stale)).delete()

            to_create: list[ArbitrationTier] = []
            to_update: list[ArbitrationTier] = []
            for key, tier in records.items():
                row = existing.get(key)
                if row is None:
                    to_create.append(ArbitrationTier(key=key, tier=tier))
                elif row.tier != tier:
                    row.tier = tier
                    to_update.append(row)

            if to_create:
                await ArbitrationTier.bulk_create(
                    to_create, ignore_conflicts=True
                )
            if to_update:
                await ArbitrationTier.bulk_update(to_update, fields=["tier"])

        logger.info(f"仲裁分级同步完成，共 {len(records)} 条")
        return len(records)

    # ══════════════════════════════════════════════════════════════════
    # 锁 / Locks
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    def _get_state_lock(cls) -> asyncio.Lock:
        """惰性创建状态锁（避免模块导入时绑定事件循环）。"""
        if cls._state_lock is None:
            cls._state_lock = asyncio.Lock()
        return cls._state_lock

    @classmethod
    def _get_reload_lock(cls) -> asyncio.Lock:
        """惰性创建刷新锁，串行化「拉取 → 落盘 → 发布」。"""
        if cls._reload_lock is None:
            cls._reload_lock = asyncio.Lock()
        return cls._reload_lock
