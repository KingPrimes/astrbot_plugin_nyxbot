"""通用数据管理 API — Plugin Pages 后端

按模型分割的 CRUD 接口，每个模型对应一个路由路径。
支持查询（分页）、创建、更新、删除、同步。
"""
from __future__ import annotations

import json
from typing import Any, Optional

from astrbot.api import logger
from astrbot.api.star import Context

from ..src.init import get_session
from ..src.model.alias import Alias
from ..src.model.nodes import Nodes

PLUGIN_NAME = "astrbot_plugin_nyxbot"

# ============================================================================
# 模型路由映射
# ============================================================================

# 模型名 → (SQLModel 类, 可搜索字段列表, 同步函数)
# 同步函数可选，用于从 CDN/API 重新拉取数据
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
        model_cls: SQLModel 类。
        search_fields: 可搜索的字段名列表。
        sync_func: 从数据源同步的函数（async callable）。
    """
    _MODEL_REGISTRY[name] = {
        "class": model_cls,
        "search_fields": search_fields or [],
        "sync_func": sync_func,
    }


def register_data_apis(context: Context) -> None:
    """注册数据管理 API。

    Args:
        context: AstrBot 上下文实例。
    """
    # 注册已知模型
    _register_model("alias", Alias, search_fields=["cn", "en"])
    _register_model("nodes", Nodes, search_fields=["name", "unique_name"])

    # 后续可通过 _register_model() 动态添加更多模型

    # ========================================================================
    # 查询（分页）
    # ========================================================================
    @context.register_web_api(
        f"/{PLUGIN_NAME}/data/<model>",
        ["GET"],
        "查询模型数据（分页）",
    )
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

        async with get_session() as session:
            from sqlmodel import select, func, or_

            # 构建查询条件
            conditions = []
            if q and search_fields:
                keyword = f"%{q}%"
                field_conditions = []
                for field_name in search_fields:
                    field = getattr(model_cls, field_name, None)
                    if field is not None:
                        field_conditions.append(field.like(keyword))
                if field_conditions:
                    conditions.append(or_(*field_conditions))

            # 总数
            count_stmt = select(func.count()).select_from(model_cls)
            if conditions:
                count_stmt = count_stmt.where(*conditions)
            total = (await session.exec(count_stmt)).one()

            # 分页查询
            stmt = select(model_cls).offset(offset).limit(size)
            if conditions:
                stmt = stmt.where(*conditions)
            results = await session.exec(stmt)
            items = results.all()

            # 序列化
            serialized = []
            for item in items:
                serialized.append(item.model_dump())

            return jsonify({"items": serialized, "total": total})

    # ========================================================================
    # 创建
    # ========================================================================
    @context.register_web_api(
        f"/{PLUGIN_NAME}/data/<model>/create",
        ["POST"],
        "添加模型记录",
    )
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

        async with get_session() as session:
            try:
                instance = model_cls(**data)
                session.add(instance)
                await session.commit()
                await session.refresh(instance)
                return jsonify({"success": True, "data": instance.model_dump()})
            except Exception as e:
                await session.rollback()
                logger.error(f"创建 {model} 记录失败: {e}")
                return jsonify({"error": str(e)}), 500

    # ========================================================================
    # 更新
    # ========================================================================
    @context.register_web_api(
        f"/{PLUGIN_NAME}/data/<model>/update",
        ["POST"],
        "修改模型记录",
    )
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

        async with get_session() as session:
            try:
                instance = await session.get(model_cls, record_id)
                if not instance:
                    return jsonify({"error": f"Record {record_id} not found"}), 404

                for key, value in data.items():
                    if hasattr(instance, key):
                        setattr(instance, key, value)

                session.add(instance)
                await session.commit()
                await session.refresh(instance)
                return jsonify({"success": True, "data": instance.model_dump()})
            except Exception as e:
                await session.rollback()
                logger.error(f"更新 {model} 记录失败: {e}")
                return jsonify({"error": str(e)}), 500

    # ========================================================================
    # 删除
    # ========================================================================
    @context.register_web_api(
        f"/{PLUGIN_NAME}/data/<model>/delete",
        ["POST"],
        "删除模型记录",
    )
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

        async with get_session() as session:
            try:
                instance = await session.get(model_cls, record_id)
                if not instance:
                    return jsonify({"error": f"Record {record_id} not found"}), 404

                await session.delete(instance)
                await session.commit()
                return jsonify({"success": True})
            except Exception as e:
                await session.rollback()
                logger.error(f"删除 {model} 记录失败: {e}")
                return jsonify({"error": str(e)}), 500

    # ========================================================================
    # 同步（从数据源重新拉取）
    # ========================================================================
    @context.register_web_api(
        f"/{PLUGIN_NAME}/data/<model>/sync",
        ["POST"],
        "从数据源同步更新模型数据",
    )
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
            return jsonify({"success": True, "message": f"模型 {model} 数据同步完成", "count": result})
        except Exception as e:
            logger.error(f"同步 {model} 数据失败: {e}")
            return jsonify({"error": str(e)}), 500

    logger.info(f"已注册数据管理 API（{len(_MODEL_REGISTRY)} 个模型）")
