"""API constants and configuration / API 常量与配置

本模块定义了 API 层使用的全局常量变量，包括：
- 纯常量：运行时不会改变的值（如 API 基础 URL、端点路径等）
- 配置驱动常量：从 PluginConfig 加载的值，在模块导入时初始化

使用方式：
    from astrbot_plugin_nyxbot.api.api import WARFRAME_WORLD_STATE
"""

from __future__ import annotations

# ============================================================================
# 纯常量 / Pure Constants
# 运行时不会改变的值，使用全大写命名约定
# ============================================================================

# Warframe 世界状态 API 基础 URL
WF_WORLD_STATE = "https://api.warframe.com/cdn/worldState.php"
"""Warframe 世界状态 API 基础 URL"""
# 官方图片获取地址
WF_PUBLIC_EXPORT = "http://content.warframe.com/PublicExport/%s"
WF_PUBLIC_EXPORT_MANIFESTS = "http://content.warframe.com/PublicExport/Manifest/%s"
WF_PUBLIC_EXPORT_INDEX = "https://origin.warframe.com/PublicExport/index_%s.txt.lzma"
# ========================
# Market APi
# =======================
# Warframe 市场 API 基础 URL
WF_MARKET_BASE_URL = "https://api.warframe.market/v2"
"""Warframe 市场 API 基础 URL"""
# 赤毒幻纹
WF_MARKET_LICH_EPHEMERAS = f"{WF_MARKET_BASE_URL}/lich/ephemeras"
"""赤毒幻纹"""
# 信条幻纹
WF_MARKET_SISTER_EPHEMERAS = f"{WF_MARKET_BASE_URL}/sister/ephemeras"
"""信条幻纹"""
# Market 物品
WF_MARKET_ITEMS = f"{WF_MARKET_BASE_URL}/items"
"""Market 物品"""
# Market 紫卡武器
WF_MARKET_RIVEN_WEAPONS = f"{WF_MARKET_BASE_URL}/riven/weapons"
"""Market 紫卡武器"""
# 赤毒武器
WF_MARKET_LICH_WEAPONS = f"{WF_MARKET_BASE_URL}/lich/weapons"
"""赤毒武器"""
# 信条武器
WF_MARKET_SISTER_WEAPONS = f"{WF_MARKET_BASE_URL}/sister/weapons"
"""信条武器"""
# Market 拍卖
WF_MARKET_SEARCH = "https://api.warframe.market/v1/auctions/search"
"""Market 拍卖"""
