import asyncio
import re

from pyrogram import Client, filters
from pyrogram.types import (
    ChosenInlineResult,
    InlineQuery,
    InlineQueryResultCachedSticker,
    InputTextMessageContent,
    Message,
)

from selfbot import listener
from selfbot.module import Module
from selfbot.utils import ikm

REGEX_PATTERN = r"^purge(me)?(\s(\d+))?$"


async def purge_filter(
    _: Client, __: filters.Filter, event: ChosenInlineResult
) -> bool:
    return event.query.strip() == "purge"


class Purge(Module):
    name = "Purge"

    async def on_startup(self) -> None:
        self.data = asyncio.Queue()
        self.lock = asyncio.Lock()

    @listener.handler(filters.regex(REGEX_PATTERN), 1)
    async def on_message(self, event: Message) -> None:
        match = re.match(REGEX_PATTERN, event.content)

        limit = 0
        if match.group(3):
            limit = int(match.group(3))

        ids = []
        if match.group(1):
            ids = [
                m.id
                async for m in event._client.search_messages(
                    event.chat.id,
                    from_user="me",
                    min_id=event.reply_to_message_id or 1,
                    max_id=event.id,
                    limit=limit or 100,
                )
            ]
        else:
            if event.reply_to_message_id:
                if limit:
                    ids = range(
                        event.reply_to_message_id, event.reply_to_message_id + limit
                    )
                else:
                    ids = range(event.reply_to_message_id, event.id)
            else:
                end = limit or 100
                ids = range(event.id - 1, event.id - (end + 1), -1)

        async with self.lock:
            await self.data.put((event.chat.id, ids))

        res = await event._client.get_inline_bot_results(self.client.bot.me.id, "purge")
        await asyncio.gather(
            event.reply_inline_bot_result(res.query_id, res.results[0].id),
            event.delete(True),
        )

    @listener.handler(filters.regex(r"^purge$"), 2)
    async def on_inline_query(self, event: InlineQuery) -> None:
        await event.answer(
            [
                InlineQueryResultCachedSticker(
                    sticker_file_id=self.client.config["sticker_file_id"],
                    reply_markup=ikm((">_", "user_id", event._client.me.id)),
                    input_message_content=InputTextMessageContent(
                        "<code>Purging...</code>"
                    ),
                )
            ],
            cache_time=900,
        )

    @listener.handler(filters.create(purge_filter, "PurgeFilter"), 3)
    async def on_chosen_inline_result(self, event: ChosenInlineResult) -> None:
        count = 0
        start = self.client.loop.time()

        async with self.lock:
            cid, ids = await self.data.get()

        for chunk in [ids[i : i + 100] for i in range(0, len(ids), 100)]:
            count += await self.client.app.delete_messages(cid, chunk)

            if count % 100 == 0:
                await asyncio.sleep(5)

        total = f"{(self.client.loop.time() - start):.3f}".rstrip("0").rstrip(".")

        await event.edit_message_text(
            f"<code>{count} Message{'' if count == 1 else 's'} Purged</code>"
            f"\n\n<b>{total} s</b>",
            reply_markup=ikm(("Close", b"0")),
        )
