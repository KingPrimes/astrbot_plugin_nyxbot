"""通用数据管理 API — Plugin Pages 后端

按模型分割的 CRUD 接口，每个模型对应一个路由路径。
支持查询（分页）、创建、更新、删除、同步。
"""
from __future__ import annotations

from typing import Any

from astrbot.api import logger

from ..util.alias_cache import invalidate_alias_cache
from ..util.search_index import invalidate as invalidate_search_index
from astrbot.api.star import Context

from ..model.alias import Alias
from ..model.arbitration_tier import ArbitrationTier
from ..model.ephemeras import Ephemeras
from ..model.export.night_wave import NightWave
from ..model.export.nodes import Nodes
from ..model.export.relic_rewards import RelicRewards
from ..model.export.relics import Relics
from ..model.export.reward.reward import Reward
from ..model.export.reward.reward_pool import RewardPool
from ..model.export.sentinels import Sentinels
from ..model.export.upgrades import Upgrades
from ..model.export.warframes import WarframeAbility, Warframes
from ..model.export.weapons import Weapons
from ..model.lich_sister_weapons import LichSisterWeapons
from ..model.mission_subscribe_user_check_type import MissionSubscribeUserCheckType
from ..model.mission_subscription import MissionSubscribe, MissionSubscribeUser
from ..model.notification import NotificationHistory
from ..model.orders_items import OrdersItems
from ..model.riven_analyse_trend import RivenAnalyseTrend
from ..model.riven_items import RivenItems
from ..model.riven_tion import RivenTion
from ..model.riven_tion_alias import RivenTionAlias
from ..model.state_translation import StateTranslation
from ..service import (
    AliasService,
    ArbitrationService,
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
)
from ..service.data_admin import DataAdminService

PLUGIN_NAME = "astrbot_plugin_nyxbot"

_INDEXED_MODELS = frozenset(
    {"alias", "orders_items", "riven_items", "lich_sister_weapons",
     "relics", "relic_rewards"}
)
"""改动这些表会改变搜索结果，增删改后必须让内存缓存失效。"""


def _invalidate_search_caches(model: str) -> None:
    """让搜索索引与别名缓存失效（只对参与搜索的表）。"""
    if model not in _INDEXED_MODELS:
        return
    invalidate_search_index()
    invalidate_alias_cache()
    logger.debug(f"{model} 数据已变更，搜索索引与别名缓存已失效")

# ============================================================================
# 模型路由映射
# ============================================================================

# 模型名 → (Tortoise Model 类, 可搜索字段列表, 同步函数)
_MODEL_REGISTRY: dict[str, dict[str, Any]] = {}


def _register_model(
    name: str,
    model_cls: type,
    search_fields: list[str] | None = None,
    sync_func=None,
) -> None:
    """注册一个数据模型。

    Args:
        name: 模型路由名称（如 "alias"）。
        model_cls: Tortoise Model 类。
        search_fields: 可搜索的字段名列表。
        sync_func: 从数据源同步的函数（async callable）。
    """
    _MODEL_REGISTRY[name] = {
        "class": model_cls,
        "search_fields": search_fields or [],
        "sync_func": sync_func,
    }


def _serialize_instance(instance: Any) -> dict:
    """将 Tortoise 模型实例序列化为字典。"""
    data = {}
    meta = getattr(instance, "_meta", None)
    if meta is None:
        return {}

    # 序列化所有数据字段
    for field_name in meta.db_fields:
        value = getattr(instance, field_name, None)
        data[field_name] = value

    # 序列化外键字段（存储关联主键值）
    for fk_field in meta.fk_fields:
        fk_value = getattr(instance, f"fk_{fk_field}_id", None)
        if fk_value is not None:
            data[fk_field] = fk_value

    # 确保包含主键
    pk_field = meta.pk_attr
    if pk_field not in data:
        data[pk_field] = getattr(instance, pk_field, None)

    return data


def register_data_apis(context: Context) -> None:
    """注册数据管理 API。

    Args:
        context: AstrBot 上下文实例。
    """
    # ========================================================================
    # 注册所有模型
    # ========================================================================

    # ── 原有模型 ──
    _register_model("alias", Alias, search_fields=["cn", "en"], sync_func=AliasService.sync_data)
    _register_model("nodes", Nodes, search_fields=["name", "uniqueName"], sync_func=NodesService.sync_data)
    _register_model(
        "arbitration_tier",
        ArbitrationTier,
        search_fields=["key", "tier"],
        sync_func=ArbitrationService.sync_tiers,
    )

    # ── Notification ──
    _register_model(
        "notification_history",
        NotificationHistory,
        search_fields=["mission_type", "mission_id", "title"],
    )

    # ── Subscription ──
    _register_model("mission_subscribe", MissionSubscribe, search_fields=["group_name", "sub_group"])
    _register_model("mission_subscribe_user", MissionSubscribeUser, search_fields=["user_id", "user_name"])
    _register_model(
        "mission_subscribe_user_check_type",
        MissionSubscribeUserCheckType,
        search_fields=["subscribe_type"],
    )

    # ── Riven ──
    _register_model("riven_tion", RivenTion, search_fields=["effect", "url_name"], sync_func=RivenService.sync_tion_data)
    _register_model("riven_tion_alias", RivenTionAlias, search_fields=["en", "cn"], sync_func=RivenService.sync_tion_alias_data)
    _register_model("riven_analyse_trend", RivenAnalyseTrend, search_fields=["name"], sync_func=RivenService.sync_analyse_trend_data)
    _register_model("riven_items", RivenItems, search_fields=["name", "slug"], sync_func=RivenService.sync_items_data)

    # ── Market ──
    _register_model("orders_items", OrdersItems, search_fields=["name", "slug"], sync_func=MarketSyncService.sync_orders_items)
    _register_model("ephemeras", Ephemeras, search_fields=["name", "slug"], sync_func=MarketSyncService.sync_ephemeras)
    _register_model("lich_sister_weapons", LichSisterWeapons, search_fields=["name", "slug"], sync_func=MarketSyncService.sync_lich_sister_weapons)

    # ── Translation ──
    _register_model(
        "state_translation",
        StateTranslation,
        search_fields=["name", "unique_name"],
        sync_func=StateTranslationService.sync_data,
    )

    # ── Exprot ──
    _register_model("night_wave", NightWave, search_fields=["name", "unique_name"], sync_func=NightWaveService.sync_data)
    _register_model("relics", Relics, search_fields=["name", "unique_name"], sync_func=RelicsService.sync_data)
    _register_model("relic_rewards", RelicRewards, search_fields=["reward_name"], sync_func=None)
    _register_model("sentinels", Sentinels, search_fields=["name", "unique_name"], sync_func=SentinelsService.sync_data)
    _register_model("upgrades", Upgrades, search_fields=["name", "unique_name"], sync_func=UpgradesService.sync_data)
    _register_model("warframes", Warframes, search_fields=["name", "unique_name"], sync_func=WarframesService.sync_data)
    _register_model("warframe_ability", WarframeAbility, search_fields=["ability_name"], sync_func=None)
    _register_model("weapons", Weapons, search_fields=["name", "unique_name"], sync_func=WeaponsService.sync_data)
    _register_model("reward_pool", RewardPool, search_fields=["unique_name"], sync_func=RewardService.sync_data)
    _register_model("reward", Reward, search_fields=["id"])

    # ========================================================================
    # 列出所有模型（供前端动态发现）
    # 注意：不要放在 /data/ 下，避免与 /data/<model> 动态路由冲突
    # ========================================================================
    async def list_models():
        """列出所有可用模型及其元数据。"""
        from quart import jsonify

        models = []
        for name, meta in _MODEL_REGISTRY.items():
            models.append({
                "name": name,
                "search_fields": meta["search_fields"],
                "has_sync": meta["sync_func"] is not None,
            })
        return jsonify({"models": models})

    context.register_web_api(
        f"/{PLUGIN_NAME}/models",
        list_models,
        ["GET"],
        "列出所有可用数据模型",
    )

    # ========================================================================
    # 查询（分页）
    # ========================================================================
    async def query_model(model: str):
        """查询指定模型的分页数据。"""
        from quart import jsonify, request

        meta = _MODEL_REGISTRY.get(model)
        if not meta:
            return jsonify({"error": f"Unknown model: {model}"}), 404

        model_cls = meta["class"]
        search_fields = meta["search_fields"]

        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", 20))
        q = request.args.get("q", "").strip()

        items, total = await DataAdminService.query(
            model_cls, search_fields, page, size, q,
        )

        serialized = [_serialize_instance(item) for item in items]
        return jsonify({"items": serialized, "total": total})

    context.register_web_api(
        f"/{PLUGIN_NAME}/data/<model>",
        query_model,
        ["GET"],
        "查询模型数据（分页）",
    )

    # ========================================================================
    # 创建
    # ========================================================================
    async def create_model_record(model: str):
        """添加新记录。"""
        from quart import jsonify, request

        meta = _MODEL_REGISTRY.get(model)
        if not meta:
            return jsonify({"error": f"Unknown model: {model}"}), 404

        model_cls = meta["class"]
        data = await request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        try:
            instance = await DataAdminService.create(model_cls, data)
            _invalidate_search_caches(model)
            return jsonify({"success": True, "data": _serialize_instance(instance)})
        except Exception as e:
            logger.error(f"创建 {model} 记录失败: {e}")
            return jsonify({"error": str(e)}), 500

    context.register_web_api(
        f"/{PLUGIN_NAME}/data/<model>/create",
        create_model_record,
        ["POST"],
        "添加模型记录",
    )

    # ========================================================================
    # 更新
    # ========================================================================
    async def update_model_record(model: str):
        """修改已有记录。"""
        from quart import jsonify, request

        meta = _MODEL_REGISTRY.get(model)
        if not meta:
            return jsonify({"error": f"Unknown model: {model}"}), 404

        model_cls = meta["class"]
        data = await request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        record_id = data.pop("id", None)
        if record_id is None:
            return jsonify({"error": "Missing 'id' field"}), 400

        try:
            instance = await DataAdminService.update(model_cls, record_id, data)
            _invalidate_search_caches(model)
            return jsonify({"success": True, "data": _serialize_instance(instance)})
        except ValueError:
            return jsonify({"error": f"Record {record_id} not found"}), 404
        except Exception as e:
            logger.error(f"更新 {model} 记录失败: {e}")
            return jsonify({"error": str(e)}), 500

    context.register_web_api(
        f"/{PLUGIN_NAME}/data/<model>/update",
        update_model_record,
        ["POST"],
        "修改模型记录",
    )

    # ========================================================================
    # 删除
    # ========================================================================
    async def delete_model_record(model: str):
        """删除记录。"""
        from quart import jsonify, request

        meta = _MODEL_REGISTRY.get(model)
        if not meta:
            return jsonify({"error": f"Unknown model: {model}"}), 404

        model_cls = meta["class"]
        data = await request.get_json()
        record_id = data.get("id") if data else None
        if record_id is None:
            return jsonify({"error": "Missing 'id' field"}), 400

        try:
            deleted = await DataAdminService.delete(model_cls, record_id)
            if not deleted:
                return jsonify({"error": f"Record {record_id} not found"}), 404
            _invalidate_search_caches(model)
            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"删除 {model} 记录失败: {e}")
            return jsonify({"error": str(e)}), 500

    context.register_web_api(
        f"/{PLUGIN_NAME}/data/<model>/delete",
        delete_model_record,
        ["POST"],
        "删除模型记录",
    )

    # ========================================================================
    # 同步（从数据源重新拉取）
    # ========================================================================
    async def sync_model(model: str):
        """从 CDN/API 数据源重新拉取数据并刷新本地库。"""
        from quart import jsonify

        meta = _MODEL_REGISTRY.get(model)
        if not meta:
            return jsonify({"error": f"Unknown model: {model}"}), 404

        sync_func = meta.get("sync_func")
        if not sync_func:
            return jsonify({"error": f"Model {model} has no sync function"}), 400

        try:
            result = await sync_func()
            # 部分同步函数用返回值表达失败（False）或返回 0 条（数据源不可用），
            # 例如 ArbitrationService.sync_tiers 拉不到 CDN 时返回 0 而不抛异常。
            if result is False or (
                isinstance(result, int)
                and not isinstance(result, bool)
                and result <= 0
            ):
                logger.warning(f"同步 {model} 未获得数据（返回值 {result!r}）")
                return jsonify(
                    {"error": f"模型 {model} 同步未获得数据，数据源可能不可用"}
                ), 502
            invalidate_search_index()
            invalidate_alias_cache()
            detail = (
                f"，共 {result} 条"
                if isinstance(result, int) and not isinstance(result, bool)
                else ""
            )
            return jsonify(
                {"success": True, "message": f"模型 {model} 数据同步完成{detail}"}
            )
        except Exception as e:
            logger.error(f"同步 {model} 数据失败: {e}")
            return jsonify({"error": str(e)}), 500

    context.register_web_api(
        f"/{PLUGIN_NAME}/data/<model>/sync",
        sync_model,
        ["POST"],
        "从数据源同步更新模型数据",
    )

    logger.info(f"已注册数据管理 API（{len(_MODEL_REGISTRY)} 个模型）")
