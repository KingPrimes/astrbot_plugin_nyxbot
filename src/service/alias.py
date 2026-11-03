"""Alias service / 别名服务层"""
from __future__ import annotations

from tortoise.exceptions import DoesNotExist
from tortoise.expressions import Q

from astrbot.api import logger

from ..model.alias import Alias


class AliasService:
    """别名查询/管理服务。"""

    @classmethod
    async def find_by_cn(cls, cn: str) -> Alias | None:
        """根据中文名称查找别名。"""
        try:
            return await Alias.get(cn=cn)
        except DoesNotExist:
            return None

    @classmethod
    async def find_by_en(cls, en: str) -> Alias | None:
        """根据英文名称查找别名。"""
        try:
            return await Alias.get(en=en)
        except DoesNotExist:
            return None

    @classmethod
    async def search(cls, keyword: str, page: int = 1, page_size: int = 20):
        """模糊搜索别名（同时搜索中文和英文）。

        Returns:
            (记录列表, 总记录数) 的元组。
        """
        offset = (page - 1) * page_size
        qs = Alias.filter(
            Q(cn__contains=keyword) | Q(en__contains=keyword)
        )
        total = await qs.count()
        items = await qs.offset(offset).limit(page_size)
        return list(items), total

    @classmethod
    async def list_all(cls, page: int = 1, page_size: int = 20):
        """分页查询所有别名。

        Returns:
            (记录列表, 总记录数) 的元组。
        """
        offset = (page - 1) * page_size
        qs = Alias.all()
        total = await qs.count()
        items = await qs.offset(offset).limit(page_size)
        return list(items), total

    @classmethod
    async def add(cls, cn: str, en: str) -> Alias:
        """添加别名。"""
        instance = Alias(cn=cn, en=en)
        await instance.save()
        return instance

    @classmethod
    async def update(cls, alias_id: int, cn: str, en: str) -> Alias | None:
        """更新别名。"""
        try:
            instance = await Alias.get(id=alias_id)
        except DoesNotExist:
            return None
        instance.cn = cn
        instance.en = en
        await instance.save()
        return instance

    @classmethod
    async def delete(cls, alias_id: int) -> bool:
        """删除别名。"""
        deleted = await Alias.filter(id=alias_id).delete()
        return deleted > 0

    @classmethod
    async def sync_data(cls) -> None:
        """从 CDN 同步别名数据到本地数据库。

        镜像原 init_alias_data() 逻辑：
        从 CdnClient 获取别名 JSON → simple_upsert 对比插入。
        """
        from ..api import CdnClient
        from .data_sync import DataSyncService

        logger.info("从 CdnClient 加载别名数据")
        data = await CdnClient.fetch_alias()
        if not data:
            logger.warning("别名数据为空，跳过初始化")
            return

        new_count, _ = await DataSyncService.simple_upsert(
            model_cls=Alias,
            data=data,
            key_field="cn",
            build_instance=lambda item: Alias(cn=item["cn"], en=item["en"]),
            prune=True,  # 整份快照：上游删掉的别名本地也要删
        )
        total = await Alias.all().count()
        logger.info(f"别名数据初始化完成，共 {total} 条记录（本次新增 {new_count} 条）")
