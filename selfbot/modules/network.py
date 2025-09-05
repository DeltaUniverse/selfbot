import asyncio
import re

from pyrogram import Client, filters
from pyrogram.raw.functions import Ping
from pyrogram.types import (
    CallbackQuery,
    ChosenInlineResult,
    InlineQuery,
    InlineQueryResultCachedSticker,
    InputTextMessageContent,
    Message,
    Update,
)

from selfbot import listener
from selfbot.module import Module
from selfbot.utils import fmtsec, ikm

pattern = re.compile(r"^ping$")


class Network(Module):
    name = "Network"

    @listener.handler(filters.regex(pattern), 1)
    async def on_message(self, event: Message) -> None:
        res = await event._client.get_inline_bot_results(self.client.bot.me.id, "ping")
        await asyncio.gather(
            event.reply_inline_bot_result(res.query_id, res.results[0].id),
            event.delete(True),
        )

    @listener.handler(filters.regex(pattern), 2)
    async def on_inline_query(self, event: InlineQuery) -> None:
        await event.answer(
            [
                InlineQueryResultCachedSticker(
                    sticker_file_id=self.client.config["sticker_file_id"],
                    reply_markup=ikm((">_", "user_id", event._client.me.id)),
                    input_message_content=InputTextMessageContent(
                        "<code>Calculating...</code>"
                    ),
                )
            ],
            cache_time=900,
        )

    @listener.handler(filters.regex(pattern), 3)
    async def on_chosen_inline_result(self, event: ChosenInlineResult) -> None:
        await self.edit(event._client, event)

    @listener.handler(filters.regex(r"^ping/(app|bot)$"), 4)
    async def on_callback_query(self, event: CallbackQuery) -> None:
        query = event.data.split("/")[1]

        await event.edit_message_text(
            "<code>Calculating...</code>",
            reply_markup=ikm((">_", "user_id", event._client.me.id)),
        )
        await self.edit(self.client.app if query == "app" else event._client, event)

    async def edit(self, client: Client, event: Update) -> None:
        result = await self.ping(client)
        await event.edit_message_text(
            result,
            reply_markup=ikm(
                [[("App", b"ping/app"), ("Bot", b"ping/bot")], [("Close", b"0")]]
            ),
        )

    async def ping(self, client: Client) -> str:
        start = self.client.loop.time()
        await client.invoke(Ping(ping_id=client.rnd_id()))

        return f"<code>Pong! {fmtsec(start)}</code>\n\n<b>{client.name.title()}</b>"
