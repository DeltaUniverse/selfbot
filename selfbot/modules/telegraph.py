import asyncio
import html
import re

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    ChosenInlineResult,
    InlineQuery,
    InlineQueryResultCachedSticker,
    InputTextMessageContent,
    Message,
    ReplyParameters,
)
from telegraph.aio import Telegraph as Graph

from selfbot import listener
from selfbot.module import Module
from selfbot.utils import fmtsec, ikm

pattern = re.compile(
    r"^graph(?:\s(?P<content>(?!-t\s.+).*?))?(?:\s-t\s(?P<title>.+))?$", re.DOTALL
)


class Telegraph(Module):
    name = "Telegraph"

    async def on_startup(self) -> None:
        self.data = asyncio.Queue()
        self.lock = asyncio.Lock()

        self.graph = Graph(access_token=None, domain="graph.org")
        await self.graph.create_account(short_name=self.client.bot.me.username)

    @listener.handler(filters.regex(pattern), 1)
    async def on_message(self, event: Message) -> None:
        data = pattern.match(event.content.html).groupdict()

        data["source"] = None

        if not data["content"]:
            reply = event.reply_to_message

            if reply.content:
                content = re.sub(r"</?spoiler\b[^>]*>", "", reply.content.html).replace(
                    "\n", "<br>"
                )

                if reply.web_page and reply.web_page.photo:
                    content = f"{content}<img src='{reply.web_page.url}'>"

                data.update({"content": content, "source": reply.link})

            else:
                return await event.edit("<code>Reply to Content or Give a Text</code>")

        async with self.lock:
            await self.data.put(data)

        res = await event._client.get_inline_bot_results(
            self.client.bot.me.id, event.content
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

        now = self.client.loop.time()
        url = None

        try:
            res = await self.graph.create_page(
                data["title"] or "Untitled",
                html_content=data["content"],
                author_name="Telegraph",
                author_url="https://t.me/Telegraph",
            )
            url = res["url"]
        except Exception as e:
            await event.edit_message_text(
                f"<code>{e.__class__.__name__}</code>\n\n<b>{fmtsec(now)}</b>",
                reply_markup=ikm(("Close", b"0")),
            )
        else:
            content = (
                f"<a href={data['source']}>Message</a>"
                if data["source"]
                else (
                    f"{html.escape(data['content'][:32])} ..."
                    if len(data["content"]) > 64
                    else html.escape(data["content"])
                )
            )

            await event.edit_message_text(
                f"<b>Telegraph Page Created</b>\n"
                f"\n  <code>Title  </code> : <code>{data['title'] or 'N/A'}</code>"
                f"\n  <code>Content</code> : {content}"
                f"\n\n<b>{fmtsec(now)}</b>",
                reply_markup=ikm([("Copy", "copy", url), ("Open", "url", url)]),
            )
