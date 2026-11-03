"""NyxBot Warframe assistant plugin / NyxBot Warframe 助手插件
"""
from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path
from typing import cast

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star

from .src.config.config import get_data_init_mode, get_qq_markdown_enabled
from .src.init.bootstrap import allows_network, bootstrap_data, is_offline_mode
from .src.init.engine import close_engine, get_engine, set_init_complete
from .src.ocr.ocr_service import OcrService
from .src.service import (
    ArbitrationService,
    WorldStateService,
)
from .src.web_api.registry import register_web_apis


class NyxBotPlugin(Star):
    """NyxBot Warframe assistant plugin / NyxBot Warframe 助手插件"""

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self._config = config
        self._init_task: asyncio.Task | None = None
        self._disable_task: asyncio.Task | None = None

    async def initialize(self):
        """Plugin initialization / 插件初始化（非阻塞）

        所有耗时操作（数据库建表、数据下载/解析/写入）放到后台协程执行，
        不阻塞 AstrBot 的启动流程。外部可通过 init_ready() 等待初始化完成。
        """
        # 在后台异步执行初始化，立即返回让 AstrBot 继续
        self._init_task = asyncio.create_task(self._do_initialize())

    async def _do_initialize(self):
        """后台执行的完整初始化逻辑。

        按 `wf_data_init_mode` 决定启动行为：

        - `auto`（默认）：核心表缺数据才导入，导入过则直接跳过；
        - `always`：忽略非空判断，每次启动重跑全量导入；
        - `never`：跳过导入，直接用现有数据库（调试用）；
        - `offline`：跳过导入，并跳过 OCR 与后台网络任务（启动最快）。

        数据导入内部按阶段隔离异常，单个数据源失败不会阻塞其它数据源。
        """
        try:
            mode = get_data_init_mode()
            logger.info(f"NyxBot 数据初始化模式: {mode}")

            # 初始化数据库（TortoiseORM 连接 + 建表）
            await get_engine()

            # 注册数据管理 API（Plugin Pages 后端）
            register_web_apis(cast(Context, self.context))
            logger.info("数据管理 API 已注册")

            tasks: list = [bootstrap_data(mode=mode)]
            if not is_offline_mode(mode):
                # 后台预热仲裁：缓存优先，never 模式完全不联网（不阻塞主流程）
                ArbitrationService.start(allow_network=allows_network(mode))
                # 初始化 OCR 引擎（PaddleOCR 模型下载 + 加载）
                tasks.append(OcrService().initialize())

            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, BaseException):
                    logger.error(f"初始化子任务失败: {result}", exc_info=result)

            # 启动 WorldState 缓存（JSON 文件持久化 + 后台自动刷新）
            if is_offline_mode(mode):
                logger.info("offline 模式：跳过仲裁预热、OCR 与 WorldState 后台刷新")
            else:
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
        self._disable_task = asyncio.create_task(
            self._disable_plugin_async(star_manager, plugin_name)
        )

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

    @filter.on_decorating_result()
    async def _decorate_markdown(self, event: AstrMessageEvent) -> None:
        """全局 Markdown 控制：配置关闭时强制纯文本。"""
        if get_qq_markdown_enabled():
            return
        result = event.get_result()
        if result is not None:
            result.use_markdown(False)

    async def terminate(self):
        """Plugin termination / 插件销毁"""
        # 取消后台初始化任务（若还在运行）
        if self._init_task and not self._init_task.done():
            self._init_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._init_task

        # 取消自停用任务（使用独立属性避免自我等待死锁）
        if self._disable_task and not self._disable_task.done():
            self._disable_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._disable_task

        # 停止 WorldState 后台刷新
        await WorldStateService.stop_cache()

        # 停止仲裁后台预热
        await ArbitrationService.stop()

        # 关闭 TortoiseORM 数据库连接
        await close_engine()
        logger.info("NyxBot plugin terminated")


# 导入 commands 包以触发所有指令 Handler 的注册
from .src import commands  # noqa: E402, F401
