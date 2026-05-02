"""
Data Sources Initialization / 数据源初始化
从 CDN 获取 Warframe 数据并保存到数据库中
"""
import aiohttp
from ..config import get_wf_data_source_cdn
from ..model.alias import Alias
from astrbot.api import logger
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import delete
from ..util import _get_db_path
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, delete
from sqlmodel.ext.asyncio.session import AsyncSession
from astrbot.api import logger


_engine = None
path = str(_get_db_path() + "/nyxbot.db")

async def get_engine():
    """获取或创建异步数据库引擎（单例）。

    首次调用时创建引擎并建表，后续调用返回同一实例。
    """
    global _engine
    if _engine is None:
        _engine = create_async_engine(f"sqlite+aiosqlite:///{path}", echo=False)
        async with _engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        logger.info(f"数据库已初始化: {path}")
    return _engine

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """获取异步数据库会话。"""
    engine = await get_engine()
    async with AsyncSession(engine) as session:
        yield session


async def init_alias_data() -> None:
    config_cdn = get_wf_data_source_cdn()
    alias_url = f"{config_cdn}/warframe/alias.json"
    logger.info(f"正在从 {alias_url} 获取别名数据...")
    
    # ---- 1. 从 CDN 获取 JSON 数据 ----
    try:
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(alias_url) as resp:
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

    # ---- 2. 写入数据库 ----
    engine = await get_engine()
    async with AsyncSession(engine) as session:
        try:
            # 清空旧数据
            await session.exec(delete(Alias))

            # 批量插入新数据
            for item in data:
                alias = Alias(cn=item["cn"], en=item["en"])
                session.add(alias)

            await session.commit()
            logger.info(f"成功保存 {len(data)} 条别名数据")
        except Exception as e:
            await session.rollback()
            logger.error(f"保存别名数据时发生错误: {e}")