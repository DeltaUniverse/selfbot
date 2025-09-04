import asyncio
import datetime
import inspect
import re

from pyrogram import Client, filters
from pyrogram.enums import MessageEntityType
from pyrogram.errors import RPCError
from pyrogram.types import (
    ChatPermissions,
    ChosenInlineResult,
    InlineQuery,
    InlineQueryResultCachedSticker,
    InputTextMessageContent,
    Message,
    ReplyParameters,
)

from selfbot import listener
from selfbot.module import Module
from selfbot.utils import ikm

RE_COMPILED = re.compile(
    r"^"
    r"(?:(?P<action>(un)?(ban|mute)|kick))"
    r"(?:\s+(?P<target>(?!\d{1,2}[mhdw]$)(?!-r$).+?))?"
    r"(?:\s+(?P<duration>\d{1,2})(?P<unit>[mhdw]))?"
    r"(?:\s+-r\s+(?P<reason>.+))?"
    r"$"
)
TIME_DELTAS = {"m": "minutes", "h": "hours", "d": "days", "w": "weeks"}


async def moderator_filter(
    _: Client, __: filters.Filter, event: ChosenInlineResult
) -> bool:
    return event.query.strip() == "moderator"


class Moderator(Module):
    name = "Moderator"

    async def on_startup(self) -> None:
        self.data = asyncio.Queue()
        self.lock = asyncio.Lock()

    @listener.handler(filters.regex(RE_COMPILED), 1)
    async def on_message(self, event: Message) -> None:
        data = RE_COMPILED.match(event.content).groupdict()

        user = data["target"]
        if user:
            if (
                event.entities
                and event.entities[0].type == MessageEntityType.TEXT_MENTION
            ):
                data["target"] = event.entities[0].user.id
            elif not target.isdigit():
                try:
                    chat = await event._client.get_chat(target, False)
                except RPCError as e:
                    return await event.edit(f"<code>{e.__class__.__name__}</code>")
                else:
                    data["target"] = chat.id
        else:
            if event.reply_to_message and event.reply_to_message.from_user:
                data["target"] = event.reply_to_message.from_user.id
            else:
                return await event.edit("<code>Reply to User or Give an ID</code>")

        data["chat_id"] = event.chat.id

        async with self.lock:
            await self.data.put(data)

        res = await event._client.get_inline_bot_results(
            self.client.bot.me.id, "moderator"
        )
        await asyncio.gather(
            event.reply_inline_bot_result(
                res.query_id,
                res.results[0].id,
                reply_parameters=ReplyParameters(
                    message_id=event.reply_to_message_id or event.id
                ),
            ),
            event.delete(True),
        )

    @listener.handler(filters.regex(r"^moderator$"), 2)
    async def on_inline_query(self, event: InlineQuery) -> None:
        await event.answer(
            [
                InlineQueryResultCachedSticker(
                    sticker_file_id=self.client.config["sticker_file_id"],
                    reply_markup=ikm((">_", "user_id", event._client.me.id)),
                    input_message_content=InputTextMessageContent("<code>...</code>"),
                )
            ],
            cache_time=900,
        )

    @listener.handler(filters.create(moderator_filter, "ModeratorFilter"), 3)
    async def on_chosen_inline_result(self, event: ChosenInlineResult) -> None:
        async with self.lock:
            data = await self.data.get()

        action = data["action"]
        target = data["target"]
        params = {"chat_id": data["chat_id"], "user_id": int(target)}

        coro = None
        unit = "N/A"

        if action in ["ban", "kick"]:
            coro = self.client.app.ban_chat_member
        elif action in ["mute", "unmute"]:
            coro = self.client.app.restrict_chat_member
            params["permissions"] = ChatPermissions(
                **{
                    k: True if action == "unmute" else False
                    for k in inspect.signature(ChatPermissions).parameters
                }
            )
        else:
            coro = self.client.app.unban_chat_member

        if action != "kick":
            if "until_date" in inspect.signature(coro).parameters and data["duration"]:
                args = {TIME_DELTAS[data["unit"]]: int(data["duration"])}
                unit = " ".join(
                    f"{v} {k.title() if v > 1 else k.removesuffix('s').title()}"
                    for k, v in args.items()
                )
                params["until_date"] = datetime.datetime.now() + datetime.timedelta(
                    **args
                )
        else:
            params["until_date"] = datetime.datetime.now() + datetime.timedelta(
                minutes=1
            )

        try:
            await coro(**params)
        except RPCError as e:
            await event.edit_message_text(
                f"<code>{e.__class__.__name__}</code>",
                reply_markup=ikm(("Close", b"0")),
            )
        else:
            past = self.verb(action, "past")
            text = (
                f"<b><a href='tg://user?id={target}'>User</a> {past}</b>"
                f"\n  <code>ID      </code> : <code>{target}</code>"
                f"\n  <code>Reason  </code> : <code>{data['reason'] or 'N/A'}</code>"
                f"\n  <code>Duration</code> : <code>{unit}</code>"
            )
            await event.edit_message_text(text, reply_markup=ikm(("Close", b"0")))

    def verb(self, text: str, tense: str) -> str:
        suffix = "ing" if tense == "present" else "ed"

        result = text.removesuffix("e")
        if result.endswith("n"):
            result += "n"

        return f"{result}{suffix}".title()
