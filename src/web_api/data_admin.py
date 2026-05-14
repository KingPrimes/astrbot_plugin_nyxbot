"""通用数据管理 API — Plugin Pages 后端

按模型分割的 CRUD 接口，每个模型对应一个路由路径。
支持查询（分页）、创建、更新、删除、同步。
"""
from __future__ import annotations

from typing import Any, Optional

from astrbot.api import logger
from astrbot.api.star import Context

from ..init import get_engine
from ..init import (
    init_alias_data,
    init_nodes_data,
    init_riven_tion_data,
    init_riven_tion_alias_data,
    init_riven_analyse_trend_data,
    init_riven_items_data,
    init_orders_items_data,
    init_ephemeras_data,
    init_lich_sister_weapons_data,
    init_state_translation_data,
    init_customs_data,
    init_mod_set_data,
    init_night_wave_data,
    init_relics_data,
    init_sentinels_data,
    init_upgrades_data,
    init_warframes_data,
    init_weapons_data,
    init_reward_data,
    init_reward_pool_data,
)
from ..model.alias import Alias
from ..model.notification import NotificationHistory
from ..model.mission_subscription import MissionSubscribe, MissionSubscribeUser
from ..model.mission_subscribe_user_check_type import MissionSubscribeUserCheckType
from ..model.ephemeras import Ephemeras
from ..model.lich_sister_weapons import LichSisterWeapons
from ..model.orders_items import OrdersItems
from ..model.riven_analyse_trend import RivenAnalyseTrend
from ..model.riven_items import RivenItems
from ..model.riven_tion import RivenTion
from ..model.riven_tion_alias import RivenTionAlias
from ..model.state_translation import StateTranslation
from ..model.exprot.customs import Customs
from ..model.exprot.mod_set import ModSet
from ..model.exprot.night_wave import NightWave
from ..model.exprot.nodes import ExprotNodes as Nodes
from ..model.exprot.relic_rewards import RelicRewards
from ..model.exprot.relics import Relics
from ..model.exprot.sentinels import Sentinels
from ..model.exprot.upgrades import Upgrades
from ..model.exprot.warframes import Warframes, WarframeAbility
from ..model.exprot.weapons import Weapons
from ..model.exprot.reward.reward import Reward
from ..model.exprot.reward.reward_pool import RewardPool

PLUGIN_NAME = "astrbot_plugin_nyxbot"

# ============================================================================
# 模型路由映射
# ============================================================================

# 模型名 → (Tortoise Model 类, 可搜索字段列表, 同步函数)
_MODEL_REGISTRY: dict[str, dict[str, Any]] = {}


def _register_model(
    name: str,
    model_cls: type,
    search_fields: Optional[list[str]] = None,
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
    _register_model("alias", Alias, search_fields=["cn", "en"], sync_func=init_alias_data)
    _register_model("nodes", Nodes, search_fields=["name", "uniqueName"], sync_func=init_nodes_data)

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
    _register_model("riven_tion", RivenTion, search_fields=["effect", "url_name"], sync_func=init_riven_tion_data)
    _register_model("riven_tion_alias", RivenTionAlias, search_fields=["en", "cn"], sync_func=init_riven_tion_alias_data)
    _register_model("riven_analyse_trend", RivenAnalyseTrend, search_fields=["name"], sync_func=init_riven_analyse_trend_data)
    _register_model("riven_items", RivenItems, search_fields=["name", "slug"], sync_func=init_riven_items_data)

    # ── Market ──
    _register_model("orders_items", OrdersItems, search_fields=["name", "slug"], sync_func=init_orders_items_data)
    _register_model("ephemeras", Ephemeras, search_fields=["name", "slug"], sync_func=init_ephemeras_data)
    _register_model("lich_sister_weapons", LichSisterWeapons, search_fields=["name", "slug"], sync_func=init_lich_sister_weapons_data)

    # ── Translation ──
    _register_model(
        "state_translation",
        StateTranslation,
        search_fields=["name", "unique_name"],
        sync_func=init_state_translation_data,
    )

    # ── Exprot ──
    _register_model("customs", Customs, search_fields=["name", "unique_name"], sync_func=init_customs_data)
    _register_model("mod_set", ModSet, search_fields=["unique_name"], sync_func=init_mod_set_data)
    _register_model("night_wave", NightWave, search_fields=["name", "unique_name"], sync_func=init_night_wave_data)
    _register_model("relics", Relics, search_fields=["name", "unique_name"], sync_func=init_relics_data)
    _register_model("relic_rewards", RelicRewards, search_fields=["reward_name"], sync_func=None)
    _register_model("sentinels", Sentinels, search_fields=["name", "unique_name"], sync_func=init_sentinels_data)
    _register_model("upgrades", Upgrades, search_fields=["name", "unique_name"], sync_func=init_upgrades_data)
    _register_model("warframes", Warframes, search_fields=["name", "unique_name"], sync_func=init_warframes_data)
    _register_model("warframe_ability", WarframeAbility, search_fields=["ability_name"], sync_func=None)
    _register_model("weapons", Weapons, search_fields=["name", "unique_name"], sync_func=init_weapons_data)
    _register_model("reward", Reward, search_fields=["item"], sync_func=init_reward_data)
    _register_model("reward_pool", RewardPool, search_fields=["unique_name"], sync_func=init_reward_pool_data)

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

        offset = (page - 1) * size

        await get_engine()

        # 构建查询
        qs = model_cls.all()
        if q and search_fields:
            from tortoise.expressions import Q
            field_conditions = []
            for field_name in search_fields:
                field_conditions.append(Q(**{f"{field_name}__contains": q}))
            if field_conditions:
                q_or = field_conditions[0]
                for fc in field_conditions[1:]:
                    q_or |= fc
                qs = qs.filter(q_or)

        # 总数
        total = await qs.count()

        # 分页查询
        items = await qs.offset(offset).limit(size)

        # 序列化
        serialized = []
        for item in items:
            serialized.append(_serialize_instance(item))

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

        await get_engine()

        try:
            instance = model_cls(**data)
            await instance.save()
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

        await get_engine()

        try:
            instance = await model_cls.get(id=record_id)
            if not instance:
                return jsonify({"error": f"Record {record_id} not found"}), 404

            for key, value in data.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)

            await instance.save()
            return jsonify({"success": True, "data": _serialize_instance(instance)})
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

        await get_engine()

        try:
            deleted = await model_cls.filter(id=record_id).delete()
            if deleted == 0:
                return jsonify({"error": f"Record {record_id} not found"}), 404
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
            await sync_func()
            return jsonify({"success": True, "message": f"模型 {model} 数据同步完成"})
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
