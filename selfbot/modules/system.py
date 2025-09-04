import asyncio
import datetime
import os
import re
import sys

from pyrogram import filters
from pyrogram.types import (
    ChosenInlineResult,
    InlineQuery,
    InlineQueryResultCachedSticker,
    InputTextMessageContent,
    Message,
)

from selfbot import listener
from selfbot.module import Module
from selfbot.utils import ikm, shell

pattern = re.compile(r"^r$")


class System(Module):
    name = "System"

    async def on_startup(self) -> None:
        date = datetime.datetime.now()

        def get_id(file: str) -> tuple | None:
            if os.path.exists(file):
                with open(file, "r") as f:
                    try:
                        data = f.readlines()
                        return data[0], float(data[1])
                    finally:
                        os.remove(file)

            return None

        data = await asyncio.to_thread(get_id, "r.txt")
        if data:
            secs = (
                date - datetime.datetime.fromtimestamp(float(data[1]))
            ).total_seconds()
            await self.client.bot.edit_inline_text(
                data[0],
                f"<code>Client Restarted</code>\n\n<b>{int(secs)} s</b>",
                reply_markup=ikm(("Close", b"0")),
            )

    @listener.handler(filters.regex(pattern), 1)
    async def on_message(self, event: Message) -> None:
        res = await event._client.get_inline_bot_results(self.client.bot.me.id, "r")
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
                    input_message_content=InputTextMessageContent("..."),
                )
            ],
            cache_time=900,
        )

    @listener.handler(filters.regex(pattern), 3)
    async def on_chosen_inline_result(self, event: ChosenInlineResult) -> None:
        def put_id(file: str, text: str) -> None:
            with open(file, "w") as f:
                f.write(text)

        if os.path.isdir(".git"):
            await shell(
                "git fetch ; git reset --hard origin/{}".format(
                    self.client.config.get("upstream_branch", "staging")
                )
            )

        await asyncio.gather(
            event.edit_message_text("<code>Updating...</code>"),
            shell("pip install -U pip && pip install -r requirements.txt"),
            asyncio.to_thread(
                put_id,
                "r.txt",
                f"{event.inline_message_id}\n{datetime.datetime.now().timestamp()}",
            ),
        )

        await event.edit_message_text("<code>Restarting...</code>")

        try:
            self.client.__idle__.cancel()
        finally:
            os.execv(sys.executable, (sys.executable, "-m", "selfbot"))
