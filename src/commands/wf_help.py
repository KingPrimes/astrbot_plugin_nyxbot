"""/wf help - Show help information / 显示帮助信息

三种交互形态（判定见 ``src/help/format.py``）：

- 开关开启且平台支持 Markdown → Markdown 文本，交互按指令能力分流：
  **无参数指令走按钮**（一击直查），**参数指令走 ``mqqapi`` 内联链接**
  （点击自动填入指令与空格，补参数发送即可）；链接菜单关闭时参数指令
  回退为按钮（点击仅提示用法）；
- 按钮与链接都不可用 → 仅 Markdown 文本（完整分节列表）；
- 平台不支持 Markdown → 同一份内容的图片卡片。

点击按钮不会重放指令消息，而是由 ``wf_help_button`` 接管，直接调用对应
指令的处理函数；需要参数的指令只回用法提示，不执行业务。链接菜单则是
``mqqapi://`` 客户端链接：点击后 QQ 把指令填入发送框，由用户确认发送。

**分页**：指令数已超过 QQ 键盘 5 行容量，``build_help_pages`` 会把按钮
按页切分并在末尾补「更多 ›」/「‹ 返回」。翻页按钮同样由
``wf_help_button`` 接管，但走**主动发送**（``context.send_message``）——
互动回复只提交 ``on_interaction_result``，带键盘的消息必须新发一条。

Three delivery shapes: Markdown text with buttons for argument-free commands
plus mqqapi inline links for parameterised ones (falling back to hint-only
buttons when links are off), plain Markdown text, or the image card. Button
keyboards are paginated because the command count exceeds QQ's 5-row cap.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

import astrbot.api.message_components as Comp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, MessageChain, MessageEventResult

from ...registry import command_prefix, wf
from ..config.config import (
    get_wf_help_buttons,
    get_wf_help_inline_links,
    get_wf_help_logo_size,
    get_wf_help_logo_url,
)
from ..help import build_help_sections
from ..help.buttons import (
    build_help_pages,
    command_from_action_id,
    is_help_button,
    is_help_page_button,
    page_from_action_id,
)
from ..help.catalog import find_help_entry
from ..help.dispatch import chain_has_media, resolve_command_handler
from ..help.format import resolve_help_format
from ..markdown.help import format_help_markdown, parse_logo_size
from ..render.card_help import render_help_card
from ..render.card_renderer import CardRenderer


def _page_hint(page_index: int, total: int) -> str:
    """分页提示 / Page position line for the help body.

    首条消息与翻页消息共用：既报页码，也告诉用户当前还有哪个方向的按钮
    可以点（第一页只有「更多」、末页只有「返回」、中间页两者都有）。
    """
    if total <= 1:
        return ""
    hint = f"第 {page_index + 1} / {total} 页"
    if page_index < total - 1:
        hint += "，点「更多 ›」查看其余指令"
    if page_index > 0:
        hint += "，点「‹ 返回」回到上一页"
    return hint


def _build_help_text(sections, pages, page_index: int = 0) -> str:
    """生成某一页的完整帮助正文 / Markdown body for one help page.

    首条消息与翻页消息共用这一份：**翻页后正文不能丢**——引言（按钮怎么用）、
    分页提示与参数指令菜单都要在，否则用户失去「其余按钮在哪、参数指令怎么
    用」的线索，只剩一排按钮（2026-11-16 用户反馈）。

    Args:
        sections: :func:`build_help_sections` 的返回值。
        pages: :func:`build_help_pages` 的返回值；空列表表示按钮不可用。
        page_index: 当前页下标（从 0 起）；越界由调用方保证不会发生。

    Returns:
        可直接放进 ``Comp.Plain`` 的 Markdown 文本。
    """
    inline_links = get_wf_help_inline_links()
    return format_help_markdown(
        sections,
        # 链接菜单关闭时正文只列参数指令，无参数指令全部由按钮承载；
        # 按钮分页后仍完整覆盖，正文不需要回退完整列表
        compact=bool(pages) and not inline_links,
        logo_url=get_wf_help_logo_url(),
        logo_size=get_wf_help_logo_size(),
        link_menu=inline_links,
        # 按钮在场时菜单只列参数指令；按钮缺席则菜单覆盖全部指令
        menu_params_only=inline_links and bool(pages),
        page_hint=_page_hint(page_index, len(pages)),
    )


@wf.command("wfhelp")
async def wf_help(
    self, event: AstrMessageEvent
) -> AsyncGenerator[MessageEventResult, None]:
    """显示 Warframe 助手指令帮助"""
    sections = build_help_sections(command_prefix)

    if resolve_help_format(event) == "markdown":
        # 按钮只在 Markdown 消息里有效（QQ 的 keyboard 依附 msg_type=2）；
        # 链接菜单开启时按钮只收无参数指令（参数指令由链接承载，点击自动
        # 填入发送框），链接关闭时按钮回退为全量（参数指令仅提示用法）
        inline_links = get_wf_help_inline_links()
        pages = (
            build_help_pages(sections, include_params=not inline_links)
            if get_wf_help_buttons()
            else []
        )
        buttons = pages[0] if pages else []
        logo_url = get_wf_help_logo_url()
        logo_size = get_wf_help_logo_size()
        if logo_url and parse_logo_size(logo_size) is None:
            logger.warning(
                f"wf_help_logo_size 应为「宽x高」（如 256x256），"
                f"当前 {logo_size!r} 将按默认 256x256 显示"
            )
        chain: list = [Comp.Plain(_build_help_text(sections, pages, 0)), *buttons]
        # 显式置位：不依赖平台默认，也让 on_decorating_result 的行为可预测
        yield event.chain_result(chain).use_markdown(True)
        return

    image_chain = await CardRenderer.render_card_to_chain_result(render_help_card, sections)
    yield event.chain_result(image_chain)


async def _send_help_page(
    plugin, event: AstrMessageEvent, action_id: str
) -> AsyncGenerator[MessageEventResult, None]:
    """重发帮助的某一页 / Re-send one help page with its keyboard.

    翻页不能走互动回复：QQ 的互动回复只提交 ``on_interaction_result``，
    键盘必须随新的 Markdown 消息发出（``context.send_message``），与
    「按钮结果带媒体」走同一条主动发送路径。

    正文与首条消息同源（:func:`_build_help_text`），只把页码换成目标页——
    翻页后仍能看到引言与参数指令菜单，不会只剩一排光秃秃的按钮。
    """
    page = page_from_action_id(action_id)
    sections = build_help_sections(command_prefix)
    pages = build_help_pages(
        sections, include_params=not get_wf_help_inline_links()
    )
    if page is None or page >= len(pages):
        yield event.plain_result("这个按钮已失效，请重新发送帮助指令")
        return

    text = _build_help_text(sections, pages, page)
    chain = MessageChain(chain=[Comp.Plain(text), *pages[page]], use_markdown_=True)
    try:
        delivered = bool(
            await plugin.context.send_message(event.unified_msg_origin, chain)
        )
    except Exception as exc:
        logger.warning(f"帮助翻页发送失败（第 {page + 1} 页）: {exc}", exc_info=True)
        yield event.plain_result("翻页失败，请重新发送帮助指令。")
        return
    if not delivered:
        logger.warning(f"帮助翻页发送失败：未找到会话所属平台（第 {page + 1} 页）")
        yield event.plain_result("翻页失败，请重新发送帮助指令。")


@wf.button_action()
async def wf_help_button(
    self, event: AstrMessageEvent
) -> AsyncGenerator[MessageEventResult, None]:
    """帮助按钮点击 → 执行对应指令 / Run the command behind a help button.

    按钮只携带指令名（``data["cmd"]``）与 id（``nyxbot:help:<指令名>``），
    这里据此路由：

    - 翻页按钮（``nyxbot:help:__page__:<页码>``）→ 重发该页键盘；
    - 需要参数的指令 → 回用法提示，不执行业务（参数没法从按钮里给）；
    - 无需参数的指令 → 直接走原处理函数，行为与手动发送完全一致。
    """
    interaction = event.get_button_interaction()
    if interaction is None:
        return

    action_id = interaction.action_id or ""
    if not is_help_button(action_id):
        return  # 不是帮助消息的按钮，不接管

    if is_help_page_button(action_id):
        async for result in _send_help_page(self, event, action_id):
            yield result
        return

    command = command_from_action_id(action_id)
    data = interaction.data
    if isinstance(data, dict) and isinstance(data.get("cmd"), str):
        command = data["cmd"].strip() or command

    entry = find_help_entry(command, build_help_sections(command_prefix))
    if entry is None:
        # 目录改过 / 消息来自旧版本
        yield event.plain_result("这个按钮已失效，请重新发送帮助指令")
        return

    if entry.arg_hint:
        example = f"\n例如：{entry.usage} {entry.arg_example}" if entry.arg_example else ""
        yield event.plain_result(f"{entry.usage} 需要{entry.arg_hint}，请手动发送。{example}")
        return

    handler = resolve_command_handler(command)
    if handler is None:
        yield event.plain_result(f"「{entry.usage}」暂不支持按钮触发，请手动发送")
        return

    logger.debug(f"帮助按钮触发指令: {command}")
    # 先收齐产出再决定投递方式：互动回复带不了媒体——qq_official 适配器的
    # Interaction 分支会无条件丢弃媒体组件（v4.29.4 源码 + 2026-11-16 真机
    # 日志证实），剩余的空 Markdown 被 QQ 以「无效 markdown content」拒收，
    # 适配器内部的主动发送回退同样失败并在约 10 秒重试后抛异常。
    # 因此带媒体的产出**直接走 context.send_message 主动发送**（富媒体上传
    # msg_type=7，c2c / 群聊均支持）；不要用 event.send()——它在按钮互动
    # 事件上是结构性错误路径（Sourcery #8 建议的「用 msg_id 被动回复」
    # 在该适配器上不可行，互动回复对媒体的支持是框架级缺失）。
    # 纯文本产出仍走互动回复，点击即达。
    results: list[MessageEventResult] = []
    try:
        async for result in handler(self, event):
            if result is not None:
                results.append(result)
    except Exception:
        # 兜底：部分指令处理函数不自捕获异常，别让按钮点击零回复
        logger.warning(f"帮助按钮触发指令执行失败: {command}", exc_info=True)
        yield event.plain_result("指令执行出错，请稍后重试，或直接手动发送指令。")
        return

    if not results:
        return

    if not any(chain_has_media(result.chain) for result in results):
        for result in results:
            yield result
        return

    for result in results:
        chain = MessageChain(
            chain=list(result.chain),
            use_markdown_=result.use_markdown_,
        )
        delivered = False
        try:
            delivered = bool(
                await self.context.send_message(event.unified_msg_origin, chain)
            )
        except Exception as exc:
            logger.warning(
                f"帮助按钮结果投递失败（{command}）: {exc}", exc_info=True
            )
            yield event.plain_result(
                "查询结果发送失败，可能被主动消息限制拦截，请直接发送指令查看。"
            )
            return
        if not delivered:
            logger.warning(f"帮助按钮结果投递失败：未找到会话所属平台（{command}）")
            yield event.plain_result("查询结果发送失败，请直接发送指令查看。")
            return
