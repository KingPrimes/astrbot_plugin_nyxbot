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

Three delivery shapes: Markdown text with buttons for argument-free commands
plus mqqapi inline links for parameterised ones (falling back to hint-only
buttons when links are off), plain Markdown text, or the image card.
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
from ..help.buttons import build_help_buttons, command_from_action_id, is_help_button
from ..help.catalog import find_help_entry
from ..help.dispatch import chain_has_media, resolve_command_handler
from ..help.format import resolve_help_format
from ..markdown.help import format_help_markdown, parse_logo_size
from ..render.card_help import render_help_card
from ..render.card_renderer import CardRenderer


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
        buttons = (
            build_help_buttons(sections, include_params=not inline_links)
            if get_wf_help_buttons()
            else []
        )
        logo_url = get_wf_help_logo_url()
        logo_size = get_wf_help_logo_size()
        if logo_url and parse_logo_size(logo_size) is None:
            logger.warning(
                f"wf_help_logo_size 应为「宽x高」（如 440x110），当前 {logo_size!r} "
                "将按默认 440x110 显示"
            )
        text = format_help_markdown(
            sections,
            compact=bool(buttons) and not inline_links,
            logo_url=logo_url,
            logo_size=logo_size,
            link_menu=inline_links,
            # 按钮在场时菜单只列参数指令；按钮缺席则菜单覆盖全部指令
            menu_params_only=inline_links and bool(buttons),
        )
        chain: list = [Comp.Plain(text), *buttons]
        # 显式置位：不依赖平台默认，也让 on_decorating_result 的行为可预测
        yield event.chain_result(chain).use_markdown(True)
        return

    image_chain = await CardRenderer.render_card_to_chain_result(render_help_card, sections)
    yield event.chain_result(image_chain)


@wf.button_action()
async def wf_help_button(
    self, event: AstrMessageEvent
) -> AsyncGenerator[MessageEventResult, None]:
    """帮助按钮点击 → 执行对应指令 / Run the command behind a help button.

    按钮只携带指令名（``data["cmd"]``）与 id（``nyxbot:help:<指令名>``），
    这里据此路由：

    - 需要参数的指令 → 回用法提示，不执行业务（参数没法从按钮里给）；
    - 无需参数的指令 → 直接走原处理函数，行为与手动发送完全一致。
    """
    interaction = event.get_button_interaction()
    if interaction is None:
        return

    action_id = interaction.action_id or ""
    if not is_help_button(action_id):
        return  # 不是帮助消息的按钮，不接管

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
    # 先收齐产出再决定投递方式：互动回复带不了媒体（AstrBot 会把媒体组件整个
    # 丢掉，剩下的空 Markdown 还会被 QQ 以「无效 markdown content」拒收），
    # 因此带媒体的产出改走主动发送（私聊直发；群聊用缓存的 msg_id 被动回复），
    # 纯文本产出仍走互动回复，点击即达。
    results: list[MessageEventResult] = []
    async for result in handler(self, event):
        if result is not None:
            results.append(result)

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
        try:
            delivered = await self.context.send_message(event.unified_msg_origin, chain)
        except Exception as exc:
            logger.warning(f"帮助按钮结果投递失败（{command}）: {exc}", exc_info=True)
            yield event.plain_result(
                "查询结果发送失败，可能被主动消息限制拦截，请直接发送指令查看。"
            )
            return
        if not delivered:
            logger.warning(f"帮助按钮结果投递失败：未找到会话所属平台（{command}）")
            yield event.plain_result("查询结果发送失败，请直接发送指令查看。")
            return
