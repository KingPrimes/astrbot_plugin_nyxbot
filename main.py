"""NyxBot Warframe assistant plugin / NyxBot Warframe 助手插件
"""
from __future__ import annotations

from typing import cast

from astrbot.api import logger, AstrBotConfig
from astrbot.api.star import Context, Star

from .src.init import init_alias_data, init_nodes_data, close_engine, get_engine
from .src.web_api.registry import register_web_apis
#from .src.task.warframe_status import WarframeStatusTask


class NyxBotPlugin(Star):
    """NyxBot Warframe assistant plugin / NyxBot Warframe 助手插件"""

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self._config = config
        #self._ws_task: WarframeStatusTask | None = None

    async def initialize(self):
        """Plugin initialization / 插件初始化"""
        # 初始化数据库（TortoiseORM 连接 + 建表）
        await get_engine()
        
        # 初始化数据（别名、节点数据）
        await init_alias_data()
        await init_nodes_data()

        # 注册数据管理 API（Plugin Pages 后端）
        register_web_apis(cast(Context, self.context))
        logger.info("数据管理 API 已注册")

        # 启动定时拉取 WorldState 任务
        #self._ws_task = WarframeStatusTask()
        #await self._ws_task.start()

    async def terminate(self):
        """Plugin termination / 插件销毁"""
        # 停止定时任务
        #if self._ws_task:
        #    await self._ws_task.stop()

        # 关闭 TortoiseORM 数据库连接
        await close_engine()
        logger.info("NyxBot plugin terminated")


# 导入 commands 包以触发所有指令 Handler 的注册
from .src import commands  # noqa: E402, F401
