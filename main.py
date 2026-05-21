"""NyxBot Warframe assistant plugin / NyxBot Warframe 助手插件
"""
from __future__ import annotations

import asyncio
from typing import cast

from astrbot.api import logger, AstrBotConfig
from astrbot.api.star import Context, Star

from .src.init import *
from .src.web_api.registry import register_web_apis
#from .src.task.warframe_status import WarframeStatusTask


class NyxBotPlugin(Star):
    """NyxBot Warframe assistant plugin / NyxBot Warframe 助手插件"""

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self._config = config
        self._init_task: asyncio.Task | None = None
        #self._ws_task: WarframeStatusTask | None = None

    async def initialize(self):
        """Plugin initialization / 插件初始化（非阻塞）

        所有耗时操作（数据库建表、数据下载/解析/写入）放到后台协程执行，
        不阻塞 AstrBot 的启动流程。外部可通过 init_ready() 等待初始化完成。
        """
        # 在后台异步执行初始化，立即返回让 AstrBot 继续
        self._init_task = asyncio.create_task(self._do_initialize())

    async def _do_initialize(self):
        """后台执行的完整初始化逻辑。"""
        try:
            # 初始化数据库（TortoiseORM 连接 + 建表）
            await get_engine()
            flag = await init_state_translation_data()
            if flag:
                set_init_complete()
                return
            else:
                # 初始化数据（别名、节点、电波任务数据）
                await init_alias_data()
                await init_riven_tion_data()
                await init_riven_tion_alias_data()
                await init_riven_analyse_trend_data()
                await init_riven_items_data()
                await init_orders_items_data()
                await init_ephemeras_data()
                await init_lich_sister_weapons_data()
                await init_night_wave_data()
                await init_relics_data()
                await init_sentinels_data()
                await init_upgrades_data()
                await init_warframes_data()
                await init_reward_pool_data()
                await init_nodes_data()
                await init_weapons_data()

                # 注册数据管理 API（Plugin Pages 后端）
                register_web_apis(cast(Context, self.context))
                logger.info("数据管理 API 已注册")

                # 启动定时拉取 WorldState 任务
                #self._ws_task = WarframeStatusTask()
                #await self._ws_task.start()

            # 标记初始化完成
            set_init_complete()
            logger.info("NyxBot 初始化完成")
        except Exception as e:
            logger.error(f"NyxBot 初始化失败: {e}", exc_info=True)
            set_init_complete()
            # 初始化失败，自动从 AstrBot 中停用当前插件
            self._schedule_self_disable()

    def _schedule_self_disable(self):
        """调度在下一个事件循环中停用当前插件。

        使用 asyncio.create_task 避免在当前的 _do_initialize 协程中直接调用
        turn_off_plugin（它内部会调用 terminate()，可能造成死锁）。
        """
        plugin_name = "astrbot_plugin_nyxbot"
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
            try:
                await self._init_task
            except asyncio.CancelledError:
                pass

        # 停止定时任务
        #if self._ws_task:
        #    await self._ws_task.stop()

        # 关闭 TortoiseORM 数据库连接
        await close_engine()
        logger.info("NyxBot plugin terminated")


# 导入 commands 包以触发所有指令 Handler 的注册
from .src import commands  # noqa: E402, F401
