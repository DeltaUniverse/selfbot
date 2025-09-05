import asyncio
import datetime
import re

from pyrogram import filters
from pyrogram.errors import RPCError
from pyrogram.types import (
    ChosenInlineResult,
    InlineQuery,
    InlineQueryResultCachedSticker,
    InputTextMessageContent,
    Message,
    ReplyParameters,
)

from selfbot import listener
from selfbot.module import Module
from selfbot.utils import fmtsec, ids, ikm

pattern = re.compile(
    r"^"
    r"sch(?P<self>me)?\s"
    r"(?P<time>\d{1,2})(?P<unit>[mhdw])"
    r"(?:\*(?P<loop>\d{1,2}))?"
    r"(?:\s(?P<text>.+))"
    r"$"
)


class Schedule(Module):
    name = "Schedule"

    async def on_startup(self) -> None:
        self.data = asyncio.Queue()
        self.lock = asyncio.Lock()

    @listener.handler(filters.regex(pattern), 1)
    async def on_message(self, event: Message) -> None:
        data = pattern.match(event.content).groupdict()

        data["reply"] = {}
        if event.external_reply and event.external_reply.message_id:
            data["reply"] = {
                "chat_id": event.external_reply.chat.id,
                "message_id": event.external_reply.message_id,
            }
        else:
            data["reply"] = {
                "chat_id": event.chat.id,
                "message_id": event.reply_to_message_id,
            }

        if event.quote and event.quote.text:
            data["reply"].update(
                {
                    "quote": event.quote.text,
                    "quote_entities": event.quote.entities,
                    "quote_position": event.quote.position,
                }
            )

        async with self.lock:
            await self.data.put(data)

        res = await event._client.get_inline_bot_results(
            self.client.bot.me.id, event.content
        )
        await asyncio.gather(
            event.reply_inline_bot_result(
                res.query_id,
                res.results[0].id,
                reply_parameters=ReplyParameters(**data["reply"]),
            ),
            event.delete(True),
        )

    @listener.handler(filters.regex(pattern), 2)
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

    @listener.handler(filters.regex(pattern), 3)
    async def on_chosen_inline_result(self, event: ChosenInlineResult) -> None:
        if self.data.empty():
            return await self.client.app.delete_messages(
                *ids(event.inline_message_id), True
            )

        async with self.lock:
            data = await self.data.get()

        time = int(data["time"])
        unit = self.period[data["unit"]]
        loop = data["loop"]
        text = data["text"].strip()

        params = {
            "chat_id": data["self"] or ids(event.inline_message_id)[0],
            "text": text,
        }

        units = unit.removesuffix("s").title() if time == 1 else unit.title()
        start = self.client.loop.time()
        count = 0

        if loop:
            for i in range(1, int(loop) + 1):
                args = {unit: time * i}

                try:
                    await self.client.app.send_message(
                        **params,
                        reply_parameters=ReplyParameters(**data["reply"]),
                        schedule_date=datetime.datetime.now()
                        + datetime.timedelta(**args),
                    )
                except RPCError:
                    break
                else:
                    count += 1

                    if i % 5 == 0:
                        await asyncio.sleep(0.5)

            await event.edit_message_text(
                f"<b>Schedule Message</b>\n"
                f"\n  <code>Self   </code> : <code>{bool(data['self'])}</code>"
                f"\n  <code>Repeat </code> : <code>{loop}</code>"
                f"\n  <code>Period </code> : <code>{time} {units}</code>"
                f"\n  <code>Failed </code> : <code>{(int(loop) - count) or 'N/A'}</code>"
                f"\n  <code>Content</code> : <code>{text}</code>"
                f"\n\n<b>{fmtsec(start)}</b>",
                reply_markup=ikm(("Close", b"0")),
            )

        else:
            args = {self.period[data["unit"]]: int(data["time"])}

            try:
                await self.client.app.send_message(
                    **params,
                    reply_parameters=ReplyParameters(**data["reply"]),
                    schedule_date=datetime.datetime.now() + datetime.timedelta(**args),
                )
            except RPCError as e:
                return await event.edit_message_text(
                    f"<code>{e.__class__.__name__}</code>",
                    reply_markup=ikm(("Close", b"0")),
                )
            else:
                await event.edit_message_text(
                    f"<b>Schedule Message</b>\n"
                    f"\n  <code>Self   </code> : <code>{bool(data['self'])}</code>"
                    f"\n  <code>Period </code> : <code>{time} {units}</code>"
                    f"\n  <code>Content</code> : <code>{text}</code>"
                    f"\n\n<b>{fmtsec(start)}</b>",
                    reply_markup=ikm(("Close", b"0")),
                )
