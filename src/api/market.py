"""Market API client / Warframe.Market API 客户端

封装 Warframe.Market API v2 的请求接口。
所有查询结果缓存在本地（TTLCache，2 分钟过期）。
"""
from __future__ import annotations

import asyncio
from enum import StrEnum, unique
from typing import Any

from astrbot.api import logger

from ..util import (
    RetryLogLevel,
    fetch_json,
    fetch_json_with_retry,
    market_cache,
)
from .api import (
    WF_MARKET_BASE_URL,
    WF_MARKET_ITEMS,
    WF_MARKET_LICH_EPHEMERAS,
    WF_MARKET_LICH_WEAPONS,
    WF_MARKET_RIVEN_WEAPONS,
    WF_MARKET_SEARCH,
    WF_MARKET_SISTER_EPHEMERAS,
    WF_MARKET_SISTER_WEAPONS,
)

# v1 auctions/search 专用请求头（镜像 Java HttpUtils.marketSendGet）
# Auction-specific headers (mirrors Java HttpUtils.marketSendGet).
_AUCTION_EXTRA_HEADERS: dict[str, str] = {
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Pragma": "no-cache",
    "Crossplay": "true",
}

# 每个缓存键一个锁，防止并发请求击穿缓存。
# Per-cache-key lock to prevent concurrent stampede on the same resource.
_cache_locks: dict[str, asyncio.Lock] = {}


class MarketClient:
    """Warframe.Market API 客户端。

    所有公共查询方法均带有 2 分钟本地缓存，避免触发 API 频率限制。
    """

    headers: dict[str, str] = {
            "Content-Type": "application/json",
            "language": "zh-hans",
        }

    @classmethod
    async def _fetch_with_cache(
        cls,
        url: str,
        cache_key: str,
        params: dict[str, Any] | None = None,
        platform: Platform | None = None,
        extra_headers: dict[str, str] | None = None,
        retry: bool = False,
        retry_count: int = 3,
        retry_delay: float = 5.0,
    ) -> dict[str, Any] | None:
        """带缓存的 GET 请求（2 分钟 TTL）。

        先从 market_cache 中查找缓存，命中则直接返回；未命中时请求 API，
        并将返回的 payload 写入缓存。

        Args:
            url: 请求 URL。
            cache_key: 缓存键（需全局唯一）。
            params: 可选的查询参数字典，会透传给底层 fetch_json。
            platform: 平台标识，默认为 None（不发送 Platform 头）。
            extra_headers: 额外的请求头，会合并到本次请求的 headers（不写入 cls.headers）。
            retry: 是否启用自动重试，默认 False 以保持向后兼容。
            retry_count: 最大重试次数（仅 retry=True 时生效）。
            retry_delay: 重试间隔秒数（仅 retry=True 时生效）。

        Returns:
            API 响应信封 {"apiVersion": str, "data": ..., "error": None}；
            网络错误或无响应时返回 None。
        """
        if cache_key is not None:
            # 缓存命中 → 直接返回 / Cache hit → return immediately
            if cache_key in market_cache:
                return market_cache[cache_key]

            # 获取或创建 per-key 锁，防止并发 stampede
            # Get or create per-key lock to prevent concurrent stampede
            lock = _cache_locks.setdefault(cache_key, asyncio.Lock())
            async with lock:
                # 双检查：前一个持有者可能已填充缓存
                # Double-check: previous holder may have filled the cache
                if cache_key in market_cache:
                    return market_cache[cache_key]
                return await cls._fetch_and_cache(
                    url, cache_key, params, platform, extra_headers,
                    retry, retry_count, retry_delay,
                )

        return await cls._fetch_and_cache(
            url, None, params, platform, extra_headers,
            retry, retry_count, retry_delay,
        )

    @classmethod
    async def _fetch_and_cache(
        cls,
        url: str,
        cache_key: str | None,
        params: dict[str, Any] | None,
        platform: Platform | None,
        extra_headers: dict[str, str] | None,
        retry: bool,
        retry_count: int,
        retry_delay: float,
    ) -> dict[str, Any] | None:
        """执行实际的 HTTP 请求并写入缓存（内部方法）。"""
        # 局部 headers 拷贝，避免并发请求互相覆盖 cls.headers["Platform"]。
        # Local headers copy — avoid concurrent requests overwriting cls.headers["Platform"].
        headers = dict(cls.headers)
        if platform is not None:
            headers["Platform"] = platform.value
        if extra_headers:
            headers.update(extra_headers)

        if retry:
            data = await fetch_json_with_retry(
                url,
                params=params,
                headers=headers,
                max_retries=retry_count,
                retry_delay=retry_delay,
            )
        else:
            data = await fetch_json(
                url,
                params=params,
                headers=headers,
            )

        if data is None:
            logger.warning(f"Market API 请求无响应: {url}")
            return None

        if cache_key is not None:
            market_cache[cache_key] = data
        return data

    # ========================================================================
    # 物品 / Items
    # ========================================================================

    @classmethod
    async def fetch_items(cls) -> dict[str, Any] | None:
        """获取所有可交易物品列表。

        Returns:
            API 响应信封 {"apiVersion": str, "data": [...], "error": None}，
            {
                "apiVersion": "0.19.1",
                "data": [
                    {
                        "id": "567af35fcbfa8f05d076a525",
                        "slug": "vital_systems_bypass",
                        "gameRef": "/Lotus/Upgrades/Mods/PvPMods/Warframe/HealthRegenLongerShieldRecharge",
                        "tags": [
                            "mod",
                            "rare",
                            "pvp",
                            "warframe"
                        ],
                        "maxRank": 3,
                        "i18n": {
                            "zh-hans": {
                                "name": "再生分流",
                                "icon": "items/images/en/vital_systems_bypass.bce5b8c6440382788dd45683c1327d49.png",
                                "thumb": "items/images/en/thumbs/vital_systems_bypass.bce5b8c6440382788dd45683c1327d49.128x128.png"
                            },
                            "en": {
                                "name": "Vital Systems Bypass",
                                "icon": "items/images/en/vital_systems_bypass.bce5b8c6440382788dd45683c1327d49.png",
                                "thumb": "items/images/en/thumbs/vital_systems_bypass.bce5b8c6440382788dd45683c1327d49.128x128.png"
                            }
                        }
                    }
                ],
                "error": null
            }
        """
        return await fetch_json_with_retry(
                url=WF_MARKET_ITEMS,
                headers=cls.headers,
                log_templates={
                    RetryLogLevel.WARNING: "获取Market 可交易物品数据失败（第 {attempt}/{max_retries} 次），{retry_delay} 秒后重试...",
                    RetryLogLevel.ERROR: "获取Market 可交易物品数据失败，已重试 {max_retries} 次，放弃",
                },
            )

    @classmethod
    async def fetch_items_orders(cls, slug: str,platform: Platform | None = None) -> dict[str, Any] | None:
        """获取指定物品的订单数据。

        Args:
            slug: 物品的 slug（如 "rhino_prime_set"）。
            platform: 要查询的平台

        Returns:
            {
                "apiVersion": "0.19.1",
                "data": [
                    {
                        "id": "uuid",
                        "type": "sell",
                        "platinum": 88,
                        "quantity": 73,
                        "rank": 73,
                        "visible": false,
                        "createdAt": "2025-12-28 08:37:52",
                        "updatedAt": "2025-06-24",
                        "itemId": "10",
                        "user": {
                            "id": "uuid",
                            "ingameName": "nickName",
                            "slug": "aliqua anim ex",
                            "avatar": "user/avatar/56a293b3d3ffb60a43942be4.png?2b19ae420608cd7b816d931eb62db438",
                            "reputation": 9,
                            "platform": "pc",
                            "crossplay": true,
                            "locale": "en",
                            "status": "offline",
                            "activity": {
                                "type": "UNKNOWN",
                                "details": "unknown",
                                "startedAt": "2025-07-12T22:05:36Z"
                            },
                            "lastSeen": "2025-07-12T22:05:36Z"
                        }
                    }
                ],
                "error": null
            }
        """
        return await cls._fetch_with_cache(
            f"{WF_MARKET_BASE_URL}/orders/item/{slug}",
            f"items_orders_{slug}_{platform}",
            platform=platform
        )

    @classmethod
    async def fetch_items_set(cls,slug:str,platform: Platform | None = None) -> dict[str, Any] | None:
        """获取指定物品的详细数据。

        Args:
            slug: 物品的 slug（如 "secura_dual_cestra"）。
            platform: 要查询的平台

        Returns:
            {
                "apiVersion": "0.23.1",
                "data": {
                    "id": "54aae292e7798909064f1575",
                    "items": [
                        {
                            "id": "54aae292e7798909064f1575",
                            "slug": "secura_dual_cestra",
                            "gameRef": "/Lotus/Weapons/Syndicates/PerrinSequence/Pistols/PSDualCestra",
                            "tags": [
                                "syndicate",
                                "weapon",
                                "secondary"
                            ],
                            "reqMasteryRank": 10,
                            "tradingTax": 2000,
                            "tradable": true,
                            "i18n": {
                                "zh-hans": {
                                    "name": "保障·锡斯特双枪",
                                    "description": "（英文：SECURA DUAL CESTRA）受佩兰数列高层人员青睐的贴身武器，这对手枪已经过改造来提升效率与击杀潜力。",
                                    "wikiLink": "https://warframe.huijiwiki.com/wiki/Secura_Dual_Cestra",
                                    "icon": "items/images/en/secura_dual_cestra.3d47a4ec6675ff774bb0da9b16c53e0e.png",
                                    "thumb": "items/images/en/thumbs/secura_dual_cestra.3d47a4ec6675ff774bb0da9b16c53e0e.128x128.png"
                                },
                                "en": {
                                    "name": "Secura Dual Cestra",
                                    "description": "The favored side-arms of Perrin Sequence executives, these pistols have been modified to improve efficiency and killing potential.",
                                    "wikiLink": "https://warframe.fandom.com/wiki/Secura_Dual_Cestra",
                                    "icon": "items/images/en/secura_dual_cestra.3d47a4ec6675ff774bb0da9b16c53e0e.png",
                                    "thumb": "items/images/en/thumbs/secura_dual_cestra.3d47a4ec6675ff774bb0da9b16c53e0e.128x128.png"
                                }
                            }
                        }
                    ]
                },
                "error": null
            }
        """
        return await cls._fetch_with_cache(
            f"{WF_MARKET_BASE_URL}/item/{slug}/set",
            f"items_set_{slug}_{platform}",
            platform=platform
        )
    # ========================================================================
    # 赤毒 / 信条 幻纹 & 武器
    # ========================================================================

    @classmethod
    async def fetch_lich_ephemeras(cls) -> dict[str, Any] | None:
        """获取赤毒幻纹列表。

        Returns:
            API 响应信封 {"apiVersion": str, "data": [...], "error": None}，
            其中 data 为赤毒幻纹列表。网络错误时返回 None。
            {
                "apiVersion": "0.23.1",
                "data": [
                    {
                        "id": "5e98548a3d9f64004f9136bb",
                        "slug": "vengeful_charge",
                        "gameRef": "/Lotus/Upgrades/Skins/Effects/Kuva/KuvaLightningEphemera",
                        "animation": "lich_ephemeras/animations/vengeful_charge.9682a7978dd10f8c63fa160d5ba1660e.webp",
                        "element": "electricity",
                        "i18n": {
                            "en": {
                                "name": "Vengeful Charge Ephemera",
                                "icon": "lich_ephemeras/images/vengeful_charge.68e07295ec11cdb303755a9f26e87f0e.png",
                                "thumb": "lich_ephemeras/images/thumbs/vengeful_charge.68e07295ec11cdb303755a9f26e87f0e.128x128.png"
                            },
                            "zh-hans": {
                                "name": "复仇充电幻纹",
                                "icon": "lich_ephemeras/images/vengeful_charge.68e07295ec11cdb303755a9f26e87f0e.png",
                                "thumb": "lich_ephemeras/images/thumbs/vengeful_charge.68e07295ec11cdb303755a9f26e87f0e.128x128.png"
                            }
                        }
                    }
                ],
                "error": null
            }
        """
        return await fetch_json_with_retry(
                url=WF_MARKET_LICH_EPHEMERAS,
                headers=cls.headers,
                log_templates={
                    RetryLogLevel.WARNING: "获取 赤毒幻纹 数据失败（第 {attempt}/{max_retries} 次），{retry_delay} 秒后重试...",
                    RetryLogLevel.ERROR: "获取 赤毒幻纹 数据失败，已重试 {max_retries} 次，放弃",
                },
            )

    @classmethod
    async def fetch_sister_ephemeras(cls) -> dict[str, Any] | None:
        """获取信条幻纹列表。

        Returns:
            API 响应信封 {"apiVersion": str, "data": [...], "error": None}，
            其中 data 为信条幻纹列表。网络错误时返回 None。
            {
                "apiVersion": "0.23.1",
                "data": [
                    {
                        "id": "60f3feb5b64404003f0bf61d",
                        "slug": "gloriana_ephemera",
                        "gameRef": "/Lotus/Upgrades/Skins/Effects/CorpusLichEphemeraC",
                        "animation": "sister_ephemeras/animations/gloriana_ephemera.61f00273d398b5ecacf93004bdacf5a8.webp",
                        "element": "cold",
                        "i18n": {
                            "zh-hans": {
                                "name": "傲骨幻纹",
                                "icon": "sister_ephemeras/images/gloriana_ephemera.0ed0559f0a1f4bd07ccef755fb71152d.png",
                                "thumb": "sister_ephemeras/images/thumbs/gloriana_ephemera.0ed0559f0a1f4bd07ccef755fb71152d.128x128.png"
                            },
                            "en": {
                                "name": "Gloriana Ephemera",
                                "icon": "sister_ephemeras/images/gloriana_ephemera.0ed0559f0a1f4bd07ccef755fb71152d.png",
                                "thumb": "sister_ephemeras/images/thumbs/gloriana_ephemera.0ed0559f0a1f4bd07ccef755fb71152d.128x128.png"
                            }
                        }
                    }
                ],
                "error": null
            }
        """
        return await fetch_json_with_retry(
                    url=WF_MARKET_SISTER_EPHEMERAS,
                    headers=cls.headers,
                    log_templates={
                        RetryLogLevel.WARNING: "获取 信条幻纹 数据失败（第 {attempt}/{max_retries} 次），{retry_delay} 秒后重试...",
                        RetryLogLevel.ERROR: "获取 信条幻纹 数据失败，已重试 {max_retries} 次，放弃",
                    },
                )

    @classmethod
    async def fetch_lich_weapons(cls) -> dict[str, Any] | None:
        """获取赤毒武器列表。

        Returns:
            API 响应信封 {"apiVersion": str, "data": [...], "error": None}，
            其中 data 为赤毒武器列表。网络错误时返回 None。
            {
                "apiVersion": "0.23.1",
                "data": [
                    {
                        "id": "5e9855993d9f64005cd702e6",
                        "slug": "kuva_drakgoon",
                        "gameRef": "/Lotus/Weapons/Grineer/KuvaLich/LongGuns/Drakgoon/KuvaDrakgoon",
                        "reqMasteryRank": 13,
                        "i18n": {
                            "en": {
                                "name": "Kuva Drakgoon",
                                "icon": "lich_weapons/images/kuva_drakgoon.1c7452cc19e0d37f8403777906f06f7a.png",
                                "thumb": "lich_weapons/images/thumbs/kuva_drakgoon.1c7452cc19e0d37f8403777906f06f7a.128x128.png"
                            },
                            "zh-hans": {
                                "name": "赤毒·龙骑兵",
                                "icon": "lich_weapons/images/kuva_drakgoon.1c7452cc19e0d37f8403777906f06f7a.png",
                                "thumb": "lich_weapons/images/thumbs/kuva_drakgoon.1c7452cc19e0d37f8403777906f06f7a.128x128.png"
                            }
                        }
                    }
                ],
                "error": null
            }
        """
        return await fetch_json_with_retry(
                        url=WF_MARKET_LICH_WEAPONS,
                        headers=cls.headers,
                        log_templates={
                            RetryLogLevel.WARNING: "获取 赤毒武器 数据失败（第 {attempt}/{max_retries} 次），{retry_delay} 秒后重试...",
                            RetryLogLevel.ERROR: "获取 赤毒武器 数据失败，已重试 {max_retries} 次，放弃",
                        },
                    )

    @classmethod
    async def fetch_sister_weapons(cls) -> dict[str, Any] | None:
        """获取信条武器列表。

        Returns:
            API 响应信封 {"apiVersion": str, "data": [...], "error": None}，
            其中 data 为信条武器列表。网络错误时返回 None。
            {
                "apiVersion": "0.23.1",
                "data": [
                    {
                        "id": "60f3feb1b64404003f0bf602",
                        "slug": "tenet_tetra",
                        "gameRef": "/Lotus/Weapons/Corpus/BoardExec/Primary/CrpBETetra/CrpBETetra",
                        "reqMasteryRank": 16,
                        "i18n": {
                            "zh-hans": {
                                "name": "信条·特拉",
                                "wikiLink": "https://warframe.fandom.com/wiki/Tenet_Tetra",
                                "icon": "sister_weapons/images/tenet_tetra.574603420c8673450692e0316abbb8cc.png",
                                "thumb": "sister_weapons/images/thumbs/tenet_tetra.574603420c8673450692e0316abbb8cc.128x128.png"
                            },
                            "en": {
                                "name": "Tenet Tetra",
                                "wikiLink": "https://warframe.fandom.com/wiki/Tenet_Tetra",
                                "icon": "sister_weapons/images/tenet_tetra.574603420c8673450692e0316abbb8cc.png",
                                "thumb": "sister_weapons/images/thumbs/tenet_tetra.574603420c8673450692e0316abbb8cc.128x128.png"
                            }
                        }
                    }
                ],
                "error": null
            }
        """
        return await fetch_json_with_retry(
                    url=WF_MARKET_SISTER_WEAPONS,
                    headers=cls.headers,
                    log_templates={
                        RetryLogLevel.WARNING: "获取 信条武器 数据失败（第 {attempt}/{max_retries} 次），{retry_delay} 秒后重试...",
                        RetryLogLevel.ERROR: "获取 信条武器 数据失败，已重试 {max_retries} 次，放弃",
                    },
                )

    # ========================================================================
    # 紫卡 / Riven
    # ========================================================================

    @classmethod
    async def fetch_riven_weapons(cls) -> dict[str, Any] | None:
        """获取紫卡武器列表。

        Returns:
            API 响应信封 {"apiVersion": str, "data": [...], "error": None}，
            其中 data 为紫卡武器列表。网络错误时返回 None。
            {
                "apiVersion": "0.23.1",
                "data": [
                    {
                        "id": "5c5ca81696e8d2003834fdcc",
                        "slug": "kulstar",
                        "gameRef": "/Lotus/Weapons/Grineer/Pistols/GrnTorpedoPistol/GrnTorpedoPistol",
                        "group": "secondary",
                        "rivenType": "pistol",
                        "disposition": 1.3,
                        "reqMasteryRank": 5,
                        "i18n": {
                            "zh-hans": {
                                "name": "杀星",
                                "icon": "items/images/en/kulstar.92736ca911a3b84f99bc9e50f24369f0.png",
                                "thumb": "items/images/en/thumbs/kulstar.92736ca911a3b84f99bc9e50f24369f0.128x128.png"
                            },
                            "en": {
                                "name": "Kulstar",
                                "icon": "items/images/en/kulstar.92736ca911a3b84f99bc9e50f24369f0.png",
                                "thumb": "items/images/en/thumbs/kulstar.92736ca911a3b84f99bc9e50f24369f0.128x128.png"
                            }
                        }
                    }
                ],
                "error": null
            }
        """
        return await fetch_json_with_retry(
                        url=WF_MARKET_RIVEN_WEAPONS,
                        headers=cls.headers,
                        log_templates={
                            RetryLogLevel.WARNING: "获取 紫卡武器 数据失败（第 {attempt}/{max_retries} 次），{retry_delay} 秒后重试...",
                            RetryLogLevel.ERROR: "获取 紫卡武器 数据失败，已重试 {max_retries} 次，放弃",
                        },
                    )

    @classmethod
    async def search_auctions(
        cls,
        weapon_url_name: str,
        *,
        auction_type: str,
        sort_by: str = "price_asc",
        # ── 紫卡专属 / Riven only ──
        positive_stats: str | None = None,
        negative_stats: str | None = None,
        polarity: str | None = None,
        mastery_rank_min: int | None = None,
        mastery_rank_max: int | None = None,
        buyout_policy: str | None = None,
        # ── 赤毒/信条专属 / Lich & Sister only ──
        element: str | None = None,
        damage_min: int | None = None,
        damage_max: int | None = None,
        has_ephemera: bool | None = None,
        # ── 通用 / Common ──
        platform: Platform | None = None,
        extra_params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """搜索拍卖 — 镜像 Java MarketRivenUtils / MarketLichsSisterUtils 的 v1 auctions/search。

        参数采用 None-skipping 风格：None 即不发送（对齐 Java "默认 ANY 时省略" 的行为）。
        各 type 默认值由调用方 service 显式传入，本方法不内置 type-specific 默认。

        Args:
            weapon_url_name: 武器 url_name（slug）。
            auction_type: "riven" / "lich" / "sister"。
            sort_by: 排序方式，"price_asc"/"price_desc"/"damage_asc"/"damage_desc"。
            positive_stats: 紫卡 — 逗号分隔的正面词条 url_name 列表，非空时发送。
            negative_stats: 紫卡 — "has"/"none"，非空时发送。
            polarity: 紫卡 — "any"/"madurai"/"vazarin"/"naramon"，非 None 时发送。
            mastery_rank_min: 紫卡 — 段位下限，非 None 时发送。
            mastery_rank_max: 紫卡 — 段位上限，非 None 时发送。
            buyout_policy: 紫卡 — "any"/"direct"/"auction"，非空且非 "any" 时发送。
            element: 赤毒/信条 — 元素类型，非空且非 "any" 时发送。
            damage_min: 赤毒/信条 — 伤害下限，非 None 时发送。
            damage_max: 赤毒/信条 — 伤害上限，非 None 时发送。
            has_ephemera: 赤毒/信条 — 是否带幻纹，非 None 时序列化为 "true"/"false" 发送。
            platform: 平台标识，默认 PC。
            extra_params: 兜底：未列出的 v1 参数（如未来扩展）。

        Returns:
            API 响应信封（v1 envelope）；网络错误时返回 None。
        """
        params: dict[str, Any] = {
            "type": auction_type,
            "weapon_url_name": weapon_url_name,
            "sort_by": sort_by,
        }
        # 字符串选项参数 —— None 或 "any" 都省略（对齐 Java "默认 ANY 时省略"）
        params.update({
            key: val
            for key, val in (
                ("positive_stats", positive_stats),
                ("negative_stats", negative_stats),
                ("buyout_policy", buyout_policy),
                ("element", element),
            )
            if val and val != "any"
        })
        # polarity：始终发送（Java riven URL 必发，包括 "any"）
        if polarity is not None:
            params["polarity"] = polarity
        # 整数参数 —— None 省略
        params.update({
            key: val
            for key, val in (
                ("mastery_rank_min", mastery_rank_min),
                ("mastery_rank_max", mastery_rank_max),
                ("damage_min", damage_min),
                ("damage_max", damage_max),
            )
            if val is not None
        })
        # 布尔参数 —— None 省略，否则序列化为小写字符串
        if has_ephemera is not None:
            params["has_ephemera"] = "true" if has_ephemera else "false"
        if extra_params:
            params.update(extra_params)

        # 确定性缓存键：所有参数按字典序拼接 + platform
        key_parts = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        cache_key = (
            f"auction_{key_parts}_{platform.value if platform else Platform.pc.value}"
        )

        return await cls._fetch_with_cache(
            WF_MARKET_SEARCH,
            cache_key,
            params=params,
            platform=platform or Platform.pc,
            extra_headers=_AUCTION_EXTRA_HEADERS,
        )

@unique
class Platform(StrEnum):
    """Warframe.Market 平台标识。"""

    pc = "pc"
    ps4 = "ps4"
    xbox = "xbox"
    switch = "switch"
    mobile = "mobile"
