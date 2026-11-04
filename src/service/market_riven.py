"""Market riven service / 紫卡市场服务

镜像 Java: MarketRivenUtils.java
"""
from __future__ import annotations

from ..config import get_whisper_fallback_lang
from ..model.market import (
    MarketRiven,
    MarketRivenPayload,
    RivenAttribute,
    RivenAuction,
    RivenItem,
    RivenOwner,
)
from ..model.riven_items import RivenItems
from ..model.riven_tion import RivenTion
from ..model.riven_tion_alias import RivenTionAlias
from .market import MarketService
from .smart_match import Candidates, Hit, Source, resolve
from .whisper import riven_whisper

# 紫卡查询默认值（镜像 Java MarketRivenUtils 默认）
# Riven query defaults — mirror Java MarketRivenUtils.
_MASTERY_MIN_DEFAULT = 7
_MASTERY_MAX_DEFAULT = 16


class MarketRivenService:
    """紫卡拍卖查询服务 / Riven auctions service."""

    @classmethod
    async def search_market_riven(
        cls,
        keyword: str,
        positive_stats: str = "",
        negative_stats: str = "",
    ) -> MarketRiven | tuple[list[str], None] | None:
        """搜索紫卡拍卖 — 镜像 Java MarketRivenUtils.marketRivenParameter()。

        支持两种输入方式（同时兼容）：
          - AstrBot 多参数风格: `/WR 武器名 暴击率,暴击伤害 无`
          - Java `-` 分隔风格:   `/WR 武器名-暴击率,暴击伤害-无`

        显式传入的 positive_stats / negative_stats 参数优先于 keyword 中 `-` 解析出来的同名值。

        Args:
            keyword: 武器名称关键词（可含 `-` 分隔的正面/负面词条）。
            positive_stats: 正面词条（逗号分隔，支持中文逗号），中文词条名将被映射到 url_name。
            negative_stats: 负面词条限定（"有"/"无"），映射为 "has"/"none"。

        Returns:
            - ``MarketRiven``：查询成功；
            - ``(候选名称列表, None)``：武器名没精确命中，交给指令层出候选；
            - ``None``：完全找不到。
        """
        # ── 1. 双语法兼容解析 ──
        kw = (keyword or "").strip()
        if "-" in kw:
            parts = [p.strip() for p in kw.split("-")]
            weapon_part = parts[0]
            pos_from_kw = parts[1] if len(parts) >= 2 else ""
            neg_from_kw = parts[2] if len(parts) >= 3 else ""
        else:
            weapon_part = kw
            pos_from_kw = ""
            neg_from_kw = ""
        # 显式参数优先
        final_pos = positive_stats.strip() or pos_from_kw
        final_neg = negative_stats.strip() or neg_from_kw

        # ── 2. 武器解析（统一 A~G 链路：精确/别名/slug/拼音/前缀）──
        resolved = await resolve(weapon_part, Source.RIVEN)
        if isinstance(resolved, Candidates):
            return ([entry.name for entry in resolved.entries], None)
        if not isinstance(resolved, Hit):
            return None
        riven_item = await RivenItems.get_or_none(id=resolved.entry.ref)
        if riven_item is None:
            return None

        # ── 3. 正面/负面词条解析 ──
        pos_url_names = await cls._resolve_positive_stats(final_pos)
        neg_value = cls._parse_negative_stat(final_neg)

        # ── 4. 请求拍卖 API（通过共享 _call_search_auctions）──
        raw_auctions = await MarketService._call_search_auctions(
            keyword,
            weapon_url_name=riven_item.slug or weapon_part,
            auction_type="riven",
            positive_stats=pos_url_names or None,
            negative_stats=neg_value or None,
            polarity="any",
            mastery_rank_min=_MASTERY_MIN_DEFAULT,
            mastery_rank_max=_MASTERY_MAX_DEFAULT,
            sort_by="price_asc",
        )
        if raw_auctions is None:
            return None

        item_name = riven_item.name or weapon_part

        if not raw_auctions:
            return MarketRiven(item_name=item_name, payload=None)

        # ── 5. 过滤 + 排序 + Top10（共享方法）──
        filtered = MarketService._filter_and_sort_auctions(raw_auctions)

        # ── 6. 收集所有出现过的 url_name，批量翻译为中文 effect ──
        url_name_to_cn = await cls._build_url_name_translation_map(filtered)

        # ── 7. 构造 pydantic 模型 ──
        auction_list = []
        for a in filtered:
            item_data = a.get("item") or {}
            owner = a.get("owner") or {}

            attrs = []
            for attr in item_data.get("attributes", []) or []:
                url_name = attr.get("url_name") or ""
                cn = url_name_to_cn.get(url_name) or url_name
                attrs.append(
                    RivenAttribute(
                        value=attr.get("value"),
                        positive=attr.get("positive"),
                        url_name=cn,
                    )
                )

            auction_list.append(
                RivenAuction(
                    buyout_price=a.get("buyout_price"),
                    starting_price=a.get("starting_price"),
                    top_bid=a.get("top_bid"),
                    visible=a.get("visible"),
                    closed=a.get("closed"),
                    platform=a.get("platform"),
                    id=a.get("id"),
                    item=RivenItem(
                        type=item_data.get("type"),
                        mod_rank=item_data.get("mod_rank"),
                        name=item_data.get("name"),
                        re_rolls=item_data.get("re_rolls"),
                        polarity=item_data.get("polarity"),
                        mastery_level=item_data.get("mastery_level"),
                        attributes=attrs,
                    ),
                    owner=RivenOwner(
                        reputation=owner.get("reputation"),
                        ingame_name=owner.get("ingame_name"),
                        status=owner.get("status"),
                        id=owner.get("id"),
                    ) if owner else None,
                )
            )

        fallback = get_whisper_fallback_lang()
        whispers = [
            entry
            for auction in auction_list
            if (
                entry := riven_whisper(
                    auction, riven_item.name, riven_item.enName, fallback
                )
            )
        ]
        return MarketRiven(
            item_name=item_name,
            payload=MarketRivenPayload(auctions=auction_list),
            whispers=whispers,
        )

    # ══════════════════════════════════════════════════════════════════
    # 武器解析 / Weapon resolution — 镜像 Java MarketRivenUtils.getRiveItems()
    # ══════════════════════════════════════════════════════════════════

    # ══════════════════════════════════════════════════════════════════
    # 词条解析 / Stat translation — 镜像 Java MarketRivenUtils.resolveStatUrlNames()
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    async def _resolve_positive_stats(cls, text: str) -> str:
        """把中文/英文词条名映射为逗号分隔的 url_name 列表。

        映射顺序：RivenTion.effect → RivenTionAlias.cn → 丢弃。
        批量查询避免 N+1 问题。

        Args:
            text: 用户输入（支持中文逗号；空字符串返回 ""）。

        Returns:
            逗号分隔的 url_name 字符串；输入为空时返回 ""。
        """
        t = (text or "").strip()
        if not t:
            return ""
        normalized = t.replace("，", ",")
        parts = [p.strip() for p in normalized.split(",") if p.strip()]
        if not parts:
            return ""

        # 批量查询 RivenTion 和 RivenTionAlias
        db_tions = await RivenTion.filter(effect__in=parts).all()
        tion_map = {t.effect: t.url_name for t in db_tions if t.url_name}

        remaining = [p for p in parts if p not in tion_map]
        alias_map: dict[str, str] = {}
        if remaining:
            db_aliases = await RivenTionAlias.filter(cn__in=remaining).all()
            alias_map = {a.cn: a.en for a in db_aliases if a.en}

        url_names: list[str] = []
        for effect in parts:
            if effect in tion_map:
                url_names.append(tion_map[effect])
            elif effect in alias_map:
                url_names.append(alias_map[effect])
        return ",".join(url_names)

    @staticmethod
    def _parse_negative_stat(text: str) -> str:
        """解析负面词条限定（"有"/"无" → "has"/"none"）。"""
        t = (text or "").strip()
        if not t:
            return ""
        return t.replace("有", "has").replace("无", "none")

    @classmethod
    async def _build_url_name_translation_map(
        cls, auctions: list[dict]
    ) -> dict[str, str]:
        """批量构建 url_name → 中文 effect 的映射表，避免循环内多次往返数据库。

        Args:
            auctions: 已过滤的 raw 拍卖列表（dict）。

        Returns:
            url_name → effect 的字典；缺失项不会出现在结果中。
        """
        url_names: set[str] = set()
        for a in auctions:
            item_data = a.get("item") or {}
            for attr in item_data.get("attributes", []) or []:
                url_name = attr.get("url_name")
                if url_name:
                    url_names.add(url_name)

        if not url_names:
            return {}

        rows = await RivenTion.filter(url_name__in=list(url_names)).all()
        return {row.url_name: row.effect for row in rows if row.url_name and row.effect}
