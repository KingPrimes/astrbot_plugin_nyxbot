"""Relic studio API / 遗物渲染后端

后台已不再提供渲染工作台页面，这组接口保留为遗物查询与渲染能力入口，
供外部调用或后续页面复用。三个端点构成「查询 → 预览 → 调版式」的闭环：

===== ============================================ ==========================
GET   ``/relic-studio/search?q=&limit=``           关键词查遗物（含奖励与杜卡德）
POST  ``/relic-studio/render``                     按版式渲染 PNG
GET   ``/relic-studio/layout`` / ``PUT``           读写版式 JSON（数据目录）
===== ============================================ ==========================

接口刻意做成「无状态」：前端把当前选中的遗物与版式一起 POST 上来，后端不缓存。
这样工作台刷新、多标签页并行都不会互相污染；后续换成「按 umo 存版式」也只是换存储层。
"""
from __future__ import annotations

import asyncio
import base64
import json
import time
from pathlib import Path
from typing import Any

from astrbot.api import logger
from astrbot.api.star import Context

from ..model.export.relics import Relics
from ..model.orders_items import OrdersItems
from ..render.branding import branding_path, load_branding, save_branding
from ..render.layout_renderer import DEFAULT_LAYOUT, normalize_layout, render_relic_layout
from ..render.theme import current_theme
from ..util.data_path import get_public_data_path

PLUGIN_NAME = "astrbot_plugin_nyxbot"

#: 版式文件（插件数据目录）。
LAYOUT_FILENAME = "relic_layout.json"

#: 查询上限（防止一次拖 200 个遗物把画布撑爆）。
MAX_QUERY = 40

#: 稀有度显示顺序：常见 → 罕见 → 稀有。
_RARITY_ORDER = {"COMMON": 0, "UNCOMMON": 1, "RARE": 2, "LEGENDARY": 3}


def layout_path() -> Path:
    return Path(get_public_data_path()) / LAYOUT_FILENAME


def load_layout() -> dict[str, Any]:
    path = layout_path()
    if not path.is_file():
        return normalize_layout(DEFAULT_LAYOUT)
    try:
        return normalize_layout(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        logger.warning(f"遗物版式读取失败（{path}）：{exc}")
        return normalize_layout(DEFAULT_LAYOUT)


def save_layout(payload: Any) -> dict[str, Any]:
    layout = normalize_layout(payload if isinstance(payload, dict) else None)
    layout_path().write_text(json.dumps(layout, ensure_ascii=False, indent=2), encoding="utf-8")
    return layout


async def _load_relics(query: str, limit: int) -> list[dict[str, Any]]:
    """按关键词查遗物，并补齐奖励与杜卡德。"""
    limit = max(1, min(MAX_QUERY, limit))
    if query:
        relics = await Relics.filter(name__icontains=query).limit(limit)
    else:
        relics = await Relics.all().limit(limit)

    payload: list[dict[str, Any]] = []
    names: list[str] = []
    for relic in relics:
        rewards = await relic.relic_rewards.all()
        rewards.sort(key=lambda item: _RARITY_ORDER.get((item.rarity or "").upper(), 9))
        items = [
            {"name": reward.rewardName, "rarity": reward.rarity, "ducats": None}
            for reward in rewards
            if reward.rewardName
        ]
        names.extend(item["name"] for item in items)
        payload.append(
            {
                "uniqueName": relic.uniqueName,
                "name": relic.name or relic.uniqueName,
                "rewards": items,
            }
        )

    if names:
        rows = await OrdersItems.filter(name__in=names).values("name", "ducats")
        ducats = {row["name"]: row["ducats"] for row in rows}
        for relic in payload:
            for reward in relic["rewards"]:
                reward["ducats"] = ducats.get(reward["name"])

    for relic in payload:
        relic["rareCount"] = sum(1 for item in relic["rewards"] if (item["rarity"] or "").upper() == "RARE")
    return payload


def register_relic_studio_apis(context: Context) -> None:
    """注册遗物工作台 API。"""

    async def search_relics():
        from quart import jsonify, request

        query = (request.args.get("q") or "").strip()
        try:
            limit = int(request.args.get("limit", 24))
        except ValueError:
            limit = 24
        items = await _load_relics(query, limit)
        return jsonify({"items": items, "total": len(items), "query": query})

    context.register_web_api(
        f"/{PLUGIN_NAME}/relic-studio/search",
        search_relics,
        ["GET"],
        "遗物查询（含奖励与杜卡德）",
    )

    async def render_relics():
        from quart import jsonify, request

        body = await request.get_json(silent=True) or {}
        unique_names = body.get("uniqueNames") or []
        if not isinstance(unique_names, list) or not unique_names:
            return jsonify({"error": "uniqueNames 不能为空"}), 400

        layout = normalize_layout(body.get("layout") if isinstance(body.get("layout"), dict) else None)

        relics = await Relics.filter(uniqueName__in=unique_names[:MAX_QUERY])
        by_name = {relic.uniqueName: relic for relic in relics}
        ordered = [by_name[name] for name in unique_names if name in by_name]

        payload: list[dict[str, Any]] = []
        for relic in ordered:
            rewards = await relic.relic_rewards.all()
            rewards.sort(key=lambda item: _RARITY_ORDER.get((item.rarity or "").upper(), 9))
            payload.append(
                {
                    "uniqueName": relic.uniqueName,
                    "name": relic.name or relic.uniqueName,
                    "rewards": [
                        {"name": reward.rewardName, "rarity": reward.rarity} for reward in rewards if reward.rewardName
                    ],
                }
            )

        names = [reward["name"] for relic in payload for reward in relic["rewards"]]
        if names:
            rows = await OrdersItems.filter(name__in=names).values("name", "ducats")
            ducats = {row["name"]: row["ducats"] for row in rows}
            for relic in payload:
                for reward in relic["rewards"]:
                    reward["ducats"] = ducats.get(reward["name"])

        theme_name = body.get("theme")
        theme = current_theme() if not theme_name else _resolve_theme(str(theme_name))

        started = time.perf_counter()
        loop = asyncio.get_running_loop()
        image = await loop.run_in_executor(None, lambda: render_relic_layout(payload, layout, theme))
        elapsed = (time.perf_counter() - started) * 1000

        # Plugin Page 的 bridge 只有 apiGet/apiPost（JSON），所以回 base64 data URL
        encoded = base64.b64encode(_encode(image)).decode("ascii")
        return jsonify(
            {
                "image": f"data:image/png;base64,{encoded}",
                "width": image.width,
                "height": image.height,
                "bytes": len(encoded) * 3 // 4,
                "ms": round(elapsed, 1),
                "count": len(payload),
            }
        )

    context.register_web_api(
        f"/{PLUGIN_NAME}/relic-studio/render",
        render_relics,
        ["POST"],
        "按版式渲染遗物卡（PNG）",
    )

    async def get_layout():
        from quart import jsonify

        return jsonify({"layout": load_layout(), "defaults": normalize_layout(DEFAULT_LAYOUT)})

    context.register_web_api(
        f"/{PLUGIN_NAME}/relic-studio/layout",
        get_layout,
        ["GET"],
        "读取遗物版式",
    )

    async def put_layout():
        from quart import jsonify, request

        body = await request.get_json(silent=True) or {}
        layout = save_layout(body.get("layout", body))
        return jsonify({"layout": layout, "saved": str(layout_path())})

    context.register_web_api(
        f"/{PLUGIN_NAME}/relic-studio/layout",
        put_layout,
        ["POST", "PUT"],
        "保存遗物版式",
    )

    async def get_branding():
        from quart import jsonify

        return jsonify({"branding": load_branding(), "path": str(branding_path())})

    context.register_web_api(
        f"/{PLUGIN_NAME}/relic-studio/branding",
        get_branding,
        ["GET"],
        "读取全局品牌设置（署名 / 看板娘）",
    )

    async def put_branding():
        from quart import jsonify, request

        body = await request.get_json(silent=True) or {}
        payload = body.get("branding", body)
        saved = save_branding(payload if isinstance(payload, dict) else None)
        return jsonify({"branding": saved, "path": str(branding_path())})

    context.register_web_api(
        f"/{PLUGIN_NAME}/relic-studio/branding",
        put_branding,
        ["POST", "PUT"],
        "保存全局品牌设置（署名 / 看板娘）",
    )


def _resolve_theme(name: str):
    """按名字取内置主题；未知值回退 dark。"""
    from ..render.theme import build_theme, normalize_mode

    return build_theme(normalize_mode(name))


def _encode(image) -> bytes:
    import io

    buffer = io.BytesIO()
    image.save(buffer, format="PNG", compress_level=1)
    return buffer.getvalue()
