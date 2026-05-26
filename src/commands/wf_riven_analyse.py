"""wf_riven_analyse - 紫卡分析指令

流程:
  1. 用户发送 /紫卡分析（或 /分析紫卡 / /Wfen）
  2. 若同消息内已带图片 → 直接 OCR 分析
  3. 否则提示发送图片，进入 30 秒会话等待
  4. 收到图片 → PaddleOCR 识别 → 武器/词条解析 → 倾向计算 → 卡片渲染

与 Java RivenAnalysePlugin 对应的别名 ``Wfen`` 来自
``CommandConstants.WARFRAME_RIVEN_ANALYSE_CMD``。
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image as PILImage

import astrbot.api.message_components as Comp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent
from astrbot.core.utils.session_waiter import session_waiter

from ...registry import wf
from ..init import init_ready
from ..render.card_renderer import CardRenderer
from ..render.card_riven_analyse import render_riven_analyse_card
from ..service.riven_analyse import RivenAnalyseService

if TYPE_CHECKING:
    from astrbot.core.utils.session_waiter import SessionController


@wf.command(name="紫卡分析", alias=["分析紫卡", "Wfen"])
async def wf_riven_analyse(self, event: AstrMessageEvent):
    """OCR 识别紫卡图片并进行属性趋势分析。"""
    await init_ready()

    # 同消息内已带图片 → 直接处理
    images = [
        c for c in event.message_obj.message
        if isinstance(c, Comp.Image)
    ]
    if images:
        async for r in _handle_with_images(event, images):
            yield r
        return

    # 进入会话等待
    yield event.plain_result("请发送一张紫卡截图（30 秒内有效）")

    try:
        @session_waiter(timeout=30, record_history_chains=False)
        async def waiter(controller: SessionController, ev: AstrMessageEvent):
            imgs = [
                c for c in ev.message_obj.message
                if isinstance(c, Comp.Image)
            ]
            if not imgs:
                await ev.send(
                    ev.plain_result(
                        '没有检测到图片，请直接发送紫卡图片，或回复"退出"取消'
                    )
                )
                if ev.message_str.strip() == "退出":
                    controller.stop()
                return
            if len(imgs) > 1:
                await ev.send(ev.plain_result("一次只接受 1 张紫卡图片"))
                return
            await _do_analyse(ev, imgs[0])
            controller.stop()

        await waiter(event)
    except TimeoutError:
        yield event.plain_result("等待超时，请重新触发指令")
    finally:
        event.stop_event()


async def _handle_with_images(
    event: AstrMessageEvent, images: list[Comp.Image],
):
    """同消息内已带图片的场景。"""
    if len(images) > 1:
        yield event.plain_result("一次只接受 1 张紫卡图片")
        return
    await _do_analyse(event, images[0])


async def _do_analyse(ev: AstrMessageEvent, img_comp: Comp.Image) -> None:
    """执行 OCR 分析并发送渲染卡片。

    session_waiter 内必须用 ``await ev.send(...)``，不能 ``yield``。
    """
    import time
    total_t0 = time.perf_counter()

    await ev.send(ev.plain_result("正在分析紫卡，请稍候…"))

    path = await img_comp.convert_to_file_path()
    logger.debug(f"紫卡分析图片路径: {path}")

    try:
        pil = PILImage.open(path).convert("RGB")
    finally:
        Path(path).unlink(missing_ok=True)

    try:
        results = await RivenAnalyseService.analyse_image(pil)
    except Exception as exc:
        logger.error(f"紫卡分析失败: {exc}", exc_info=True)
        await ev.send(ev.plain_result(f"紫卡分析失败: {exc}"))
        return

    if not results:
        await ev.send(ev.plain_result("OCR 未识别到紫卡武器名"))
        return

    # 渲染多卡片并发送
    render_t0 = time.perf_counter()
    renderer = CardRenderer()
    loop = asyncio.get_running_loop()
    img_bytes = await loop.run_in_executor(
        None,
        lambda: CardRenderer.render_to_bytes(
            render_riven_analyse_card(renderer, results)
        ),
    )
    logger.debug(
        "卡片渲染耗时 %.2fs (%d 张卡片)",
        time.perf_counter() - render_t0, len(results),
    )
    await ev.send(ev.chain_result([Comp.Image.fromBytes(img_bytes)]))
    logger.debug(
        "紫卡分析指令总耗时 %.2fs (含图片转换+OCR+解析+计算+渲染)",
        time.perf_counter() - total_t0,
    )
