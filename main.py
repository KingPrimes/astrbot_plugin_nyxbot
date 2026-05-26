"""NyxBot Warframe assistant plugin / NyxBot Warframe 助手插件
"""
from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path
from typing import cast

from astrbot.api import AstrBotConfig, logger
from astrbot.api.star import Context, Star

from .src.init.engine import close_engine, get_engine, set_init_complete
from .src.ocr.ocr_service import OcrService
from .src.service import (
    AliasService,
    MarketSyncService,
    NightWaveService,
    NodesService,
    RelicsService,
    RewardService,
    RivenService,
    SentinelsService,
    StateTranslationService,
    UpgradesService,
    WarframesService,
    WeaponsService,
    WorldStateService,
)
from .src.web_api.registry import register_web_apis

#from .src.task.warframe_status import WarframeStatusTask


class NyxBotPlugin(Star):
    """NyxBot Warframe assistant plugin / NyxBot Warframe 助手插件"""

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self._config = config
        self._init_task: asyncio.Task | None = None

    async def initialize(self):
        """Plugin initialization / 插件初始化（非阻塞）

        所有耗时操作（数据库建表、数据下载/解析/写入）放到后台协程执行，
        不阻塞 AstrBot 的启动流程。外部可通过 init_ready() 等待初始化完成。
        """
        # 在后台异步执行初始化，立即返回让 AstrBot 继续
        self._init_task = asyncio.create_task(self._do_initialize())

    async def _do_initialize(self):
        """后台执行的完整初始化逻辑。

        各 Service.sync_*() 方法独立访问各自数据库表，无跨组依赖。
        get_engine() 内部有单例保护，并发调用安全。
        return_exceptions=True 确保一个数据源失败不阻塞其他数据源。
        - Stub Service 串行执行（无实际开销）
        """
        try:
            # 初始化数据库（TortoiseORM 连接 + 建表）
            await get_engine()

            # 初始化 OCR 引擎（PaddleOCR 模型下载 + 加载，一次性完成）
            await OcrService().initialize()

            # StateTranslation 必须最先执行（导出文件下载依赖）
            if not await StateTranslationService.sync_data():
                set_init_complete()
                return

            # 所有独立数据源一次性并发拉取（无跨组依赖，最大化并发）
            results = await asyncio.gather(
                # CDN 数据源
                AliasService.sync_data(),
                RivenService.sync_tion_data(),
                RivenService.sync_tion_alias_data(),
                RivenService.sync_analyse_trend_data(),
                RewardService.sync_data(),
                # Market API 数据源
                RivenService.sync_items_data(),
                MarketSyncService.sync_orders_items(),
                MarketSyncService.sync_ephemeras(),
                MarketSyncService.sync_lich_sister_weapons(),
                # 导出文件数据源
                NightWaveService.sync_data(),
                NodesService.sync_data(),
                WeaponsService.sync_data(),
                return_exceptions=True,
            )
            for i, result in enumerate(results):
                if isinstance(result, BaseException):
                    logger.error(f"数据同步任务 #{i} 失败: {result}", exc_info=result)

            # Stub Service（无网络开销，串行即可）
            await RelicsService.sync_data()
            await SentinelsService.sync_data()
            await UpgradesService.sync_data()
            await WarframesService.sync_data()

            # 注册数据管理 API（Plugin Pages 后端）
            register_web_apis(cast(Context, self.context))
            logger.info("数据管理 API 已注册")

            # 启动 WorldState 缓存（JSON 文件持久化 + 后台自动刷新）
            await WorldStateService.start_cache()

            # 标记初始化完成
            set_init_complete()
            logger.info("NyxBot 初始化完成")
        except Exception as e:
            logger.exception(f"NyxBot 初始化失败: {e}")
            set_init_complete()
            # 初始化失败，自动从 AstrBot 中停用当前插件
            self._schedule_self_disable()

    def _schedule_self_disable(self):
        """调度在下一个事件循环中停用当前插件。

        使用 asyncio.create_task 避免在当前的 _do_initialize 协程中直接调用
        turn_off_plugin（它内部会调用 terminate()，可能造成死锁）。
        """
        plugin_name = Path(__file__).resolve().parent.name
        star_manager = getattr(self.context, "_star_manager", None)
        if star_manager is None:
            logger.error(f"无法获取 StarManager，跳过停用插件 {plugin_name}")
            return
        asyncio.create_task(self._disable_plugin_async(star_manager, plugin_name))

    async def _disable_plugin_async(self, star_manager, plugin_name: str):
        """异步停用插件并提示用户。"""
        try:
            await star_manager.turn_off_plugin(plugin_name)
            logger.warning(
                f"插件 {plugin_name} 初始化数据失败，已自动停用。"
                "请检查网络连接或数据源后重新启用插件尝试。"
            )
        except Exception as e:
            logger.error(f"自动停用插件 {plugin_name} 失败: {e}", exc_info=True)

    async def terminate(self):
        """Plugin termination / 插件销毁"""
        # 等待后台初始化任务完成
        if self._init_task and not self._init_task.done():
            self._init_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._init_task

        # 停止 WorldState 后台刷新
        await WorldStateService.stop_cache()

        # 关闭 TortoiseORM 数据库连接
        await close_engine()
        logger.info("NyxBot plugin terminated")


# 导入 commands 包以触发所有指令 Handler 的注册
from .src import commands  # noqa: E402, F401
