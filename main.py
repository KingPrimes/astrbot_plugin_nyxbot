"""NyxBot Warframe assistant plugin / NyxBot Warframe 助手插件
"""

from __future__ import annotations

from astrbot.api import logger, AstrBotConfig
from astrbot.api.star import Context, Star


class NyxBotPlugin(Star):
    """NyxBot Warframe assistant plugin / NyxBot Warframe 助手插件"""

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)

    async def initialize(self):
        """Plugin initialization / 插件初始化"""

    async def terminate(self):
        """Plugin termination / 插件销毁"""
        logger.info("NyxBot plugin terminated")


# 导入 commands 包以触发所有指令 Handler 的注册
# Import the commands package to trigger handler registration for all commands
from . import commands  # noqa: E402, F401
