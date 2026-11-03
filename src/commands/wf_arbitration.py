"""wf_arbitration - /仲裁 / 仲裁表 / 更新仲裁 / 更新分级

对齐 Go:
  - ``/仲裁``：``warframe.DefaultArbitration().GetArbitration()`` + ``draw.DrawArbitration``
  - ``/仲裁表``：``GetArbitrationList()`` + ``draw.DrawArbitrations``
  - ``/更新仲裁``：``ArbitrationCache.Reload()``
  - ``/更新分级``：``DataImporter.UpdateArbitrationTiers()``
"""
from __future__ import annotations

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from ...registry import wf
from ..render.card_arbitration import (
    render_arbitration_card,
    render_arbitration_list_card,
)
from ..render.card_renderer import CardRenderer
from ..service.arbitration import ArbitrationService


def _is_admin(plugin, event: AstrMessageEvent) -> bool:
    """管理员判定：群主/群管理员，或 AstrBot 全局 admins_id。

    Go 版用数据库 BotAdmin 的 PermSuperAdmin；AstrBot 侧没有等价表，
    这里用 AstrBot 自带的管理员语义代偿，后续接入 RBAC 后可收紧。
    """
    role = str(getattr(event, "role", "") or "")
    if role in {"admin", "owner"}:
        return True
    try:
        admins = plugin.context.get_config().get("admins_id", [])
    except Exception:
        return False
    sender_id = str(event.get_sender_id())
    return sender_id in {str(admin) for admin in admins}


@wf.command("仲裁")
async def wf_arbitration(self, event: AstrMessageEvent):
    """查看当前仲裁任务。"""
    arbitration = await ArbitrationService.get_arbitration()
    if arbitration is None:
        yield event.plain_result("暂无当前仲裁数据")
        return

    views = await ArbitrationService.to_views([arbitration])
    chain = await CardRenderer.render_card_to_chain_result(
        render_arbitration_card, views[0]
    )
    yield event.chain_result(chain)


@wf.command("仲裁表")
async def wf_arbitration_table(self, event: AstrMessageEvent):
    """查看值得参与的未来仲裁列表（S/A/B 分级，最多 10 条）。"""
    entries = await ArbitrationService.get_arbitration_list()
    if not entries:
        yield event.plain_result("暂无待参与的仲裁数据")
        return

    views = await ArbitrationService.to_views(entries)
    chain = await CardRenderer.render_card_to_chain_result(
        render_arbitration_list_card, views
    )
    yield event.chain_result(chain)


@wf.command("更新仲裁")
async def wf_update_arbitration(self, event: AstrMessageEvent):
    """重拉仲裁时间表（管理员）。"""
    if not _is_admin(self, event):
        yield event.plain_result("该指令仅管理员可用")
        return

    yield event.plain_result("已发布任务，正在更新！")
    try:
        success = await ArbitrationService.reload()
    except Exception as exc:
        logger.exception(f"更新仲裁失败: {exc}")
        success = False
    yield event.plain_result(
        "仲裁更新完成！" if success else "仲裁更新失败！"
    )


@wf.command("更新分级")
async def wf_update_arbitration_tiers(self, event: AstrMessageEvent):
    """重拉仲裁节点分级（管理员）。"""
    if not _is_admin(self, event):
        yield event.plain_result("该指令仅管理员可用")
        return

    yield event.plain_result("已发布任务，正在更新！")
    try:
        count = await ArbitrationService.sync_tiers()
    except Exception as exc:
        logger.exception(f"更新仲裁分级失败: {exc}")
        count = 0
    yield event.plain_result(
        f"分级更新完成！共 {count} 条" if count else "分级更新失败！"
    )
