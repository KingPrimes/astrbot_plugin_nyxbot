"""
Data Sources Initialization / 数据源初始化
从 CDN 获取 Warframe 数据并保存到 SQLite 数据库中。
"""
from __future__ import annotations

import aiohttp
from typing import AsyncGenerator, Optional

from aiohttp import ClientTimeout
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlmodel import SQLModel, delete
from sqlmodel.ext.asyncio.session import AsyncSession
from astrbot.api import logger

from ..config import get_wf_data_source_cdn
from ..model.alias import Alias
from ..model.nodes import Nodes
from ..util import _get_db_path


_engine: Optional[AsyncEngine] = None
_db_path: str = _get_db_path() + "/nyxbot.db"

# 超时设置
_DEFAULT_TIMEOUT = ClientTimeout(total=30)


async def get_engine() -> AsyncEngine:
    """获取或创建异步数据库引擎（单例）。

    首次调用时创建引擎并建表，后续调用返回同一实例。
    """
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            f"sqlite+aiosqlite:///{_db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        async with _engine.begin() as conn:
            # 建表（扫描所有继承 SQLModel 的模型）
            await conn.run_sync(SQLModel.metadata.create_all)
        logger.info(f"数据库已初始化: {_db_path}")
    return _engine


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """获取异步数据库会话。"""
    engine = await get_engine()
    async with AsyncSession(engine) as session:
        yield session


async def close_engine() -> None:
    """关闭数据库引擎。"""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None
        logger.info("数据库引擎已关闭")


async def init_alias_data() -> None:
    """从 CDN 获取别名数据并写入 SQLite。

    流程：拉取 JSON → 清空旧数据 → 批量插入新数据。
    """
    config_cdn = get_wf_data_source_cdn()
    alias_url = f"{config_cdn}/warframe/alias.json"
    logger.info(f"正在从 {alias_url} 获取别名数据...")

    try:
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(alias_url, timeout=_DEFAULT_TIMEOUT) as resp:
                if resp.status != 200:
                    logger.error(f"获取别名数据失败，HTTP 状态码: {resp.status}")
                    return
                data = await resp.json(content_type=None)
    except Exception as e:
        logger.error(f"获取别名数据时发生网络错误: {e}")
        return

    if not data or not isinstance(data, list):
        logger.error("别名数据格式不正确，期望非空 JSON 数组")
        return

    engine = await get_engine()
    async with AsyncSession(engine) as session:
        try:
            # 清空旧数据
            await session.exec(delete(Alias))

            # 批量插入新数据（使用 model_validate 以支持 Field alias）
            for item in data:
                alias = Alias.model_validate(item)
                session.add(alias)

            await session.commit()
            logger.info(f"成功保存 {len(data)} 条别名数据")
        except Exception as e:
            await session.rollback()
            logger.error(f"保存别名数据时发生错误: {e}")


async def init_nodes_data() -> None:
    """从 CDN 获取星图节点数据并写入 SQLite。

    流程：拉取 JSON → 清空旧数据 → 批量插入新数据。
    """
    config_cdn = get_wf_data_source_cdn()
    nodes_url = f"{config_cdn}/warframe/nodes.json"
    logger.info(f"正在从 {nodes_url} 获取节点数据...")

    try:
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(nodes_url, timeout=_DEFAULT_TIMEOUT) as resp:
                if resp.status != 200:
                    logger.error(f"获取节点数据失败，HTTP 状态码: {resp.status}")
                    return
                data = await resp.json(content_type=None)
    except Exception as e:
        logger.error(f"获取节点数据时发生网络错误: {e}")
        return

    if not data or not isinstance(data, list):
        logger.error("节点数据格式不正确，期望非空 JSON 数组")
        return

    engine = await get_engine()
    async with AsyncSession(engine) as session:
        try:
            # 清空旧数据
            await session.exec(delete(Nodes))

            # 批量插入新数据（使用 model_validate 以支持 Field alias）
            for item in data:
                node = Nodes.model_validate(item)
                session.add(node)

            await session.commit()
            logger.info(f"成功保存 {len(data)} 条节点数据")
        except Exception as e:
            await session.rollback()
            logger.error(f"保存节点数据时发生错误: {e}")
