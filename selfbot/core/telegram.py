import abc
import asyncio
import functools
import os
import pathlib
import signal

from pyrogram import Client
from pyrogram import filters as flt
from pyrogram.enums import ParseMode
from pyrogram.handlers import (
    CallbackQueryHandler,
    ChosenInlineResultHandler,
    InlineQueryHandler,
    MessageHandler,
)
from pyrogram.raw.types import (
    UpdateBotInlineQuery,
    UpdateBotInlineSend,
    UpdateInlineBotCallbackQuery,
    UpdateNewChannelMessage,
    UpdateNewMessage,
)
from pyrogram.storage import FileStorage
from pyrogram.types import LinkPreviewOptions, Update

commons = {
    "workdir": "./selfbot/storage/",
    "parse_mode": ParseMode.HTML,
    "sleep_threshold": 900,
    "max_message_cache_size": 0,
    "link_preview_options": LinkPreviewOptions(is_disabled=True),
}


class Telegram(abc.ABC):
    def __init__(self, **kwargs) -> None:
        self.handlers = {}
        self.__idle__ = None

        self.app = self._app
        self.bot = self._bot

        super().__init__(**kwargs)

    async def run(self) -> None:
        if self.__idle__ and not self.__idle__.done():
            raise RuntimeError("Selfbot Running")

        try:
            await self.start()
            self.logger.info("Client Started")
        except Exception as e:
            self.logger.error(str(e))
        else:
            await self.idle()
        finally:
            await self.stop()
            self.logger.info("Client Stopped")

    async def start(self) -> None:
        if not os.path.exists(f"{commons['workdir']}/{self.app.name}.session"):
            async with Client(
                self.app.name, session_string=self.config["session_string"]
            ) as client:
                await self.migrate(
                    client, FileStorage(client.name, pathlib.Path(commons["workdir"]))
                )

        await asyncio.gather(self.app.start(), self.bot.start())
        await self.app.resolve_peer(self.bot.me.username)

        await asyncio.to_thread(self.loads)
        await self.dispatch("startup")

        for cred in ["api_id", "api_hash", "bot_token", "session_string"]:
            self.config.pop(cred, None)

    async def idle(self) -> None:
        if self.__idle__ and not self.__idle__.is_set():
            raise RuntimeError("Selfbot Idling")

        signames = (signal.SIGINT, signal.SIGTERM, signal.SIGABRT)

        def sighandler(signum: int) -> None:
            if self.__idle__:
                self.__idle__.set()

        for signame in signames:
            self.loop.add_signal_handler(
                signame, functools.partial(sighandler, signame)
            )

        self.__idle__ = asyncio.Event()

        try:
            await self.__idle__.wait()
        finally:
            for signame in signames:
                with contextlib.suppress(Exception):
                    self.loop.remove_signal_handler(signame)

    def updates(self) -> None:
        fltapp = flt.user(self.app.me.id)
        events = {
            "message": (self.app, MessageHandler, flt.me, 0),
            "callback_query": (self.bot, CallbackQueryHandler, fltapp, 0),
            "chosen_inline_result": (self.bot, ChosenInlineResultHandler, fltapp, 0),
            "inline_query": (self.bot, InlineQueryHandler, fltapp, 0),
        }

        for name, (client, handler, filters, group) in events.items():
            if name in self.handlers:
                client.remove_handler(*self.handlers.pop(name))

            if name in self.listeners and self.listeners[name]:

                async def callback(_: Client, event: Update, bound=name) -> None:
                    await self.dispatch(bound, event)

                dispatcher = (handler(callback, filters), group)

                try:
                    client.add_handler(*dispatcher)
                finally:
                    self.handlers[name] = dispatcher

    @staticmethod
    async def migrate(client: Client, storage: FileStorage) -> None:
        attrs = [
            "dc_id",
            "api_id",
            "test_mode",
            "auth_key",
            "date",
            "user_id",
            "is_bot",
        ]
        creds = await asyncio.gather(
            *(getattr(client.storage, attr)() for attr in attrs)
        )

        await storage.open()
        await asyncio.gather(
            *(getattr(storage, attr)(cred) for attr, cred in zip(attrs, creds))
        )

    @property
    def _app(self) -> Client:
        client = Client("app", no_joined_notifications=True, **commons)

        client.dispatcher.update_parsers = {
            k: v
            for k, v in client.dispatcher.update_parsers.items()
            if k in (UpdateNewChannelMessage, UpdateNewMessage)
        }
        setattr(client, "workers", len(client.dispatcher.update_parsers))

        return client

    @property
    def _bot(self) -> Client:
        client = Client(
            "bot",
            api_id=self.config["api_id"],
            api_hash=self.config["api_hash"],
            bot_token=self.config["bot_token"],
            **commons,
        )

        client.dispatcher.update_parsers = {
            k: v
            for k, v in client.dispatcher.update_parsers.items()
            if k
            in (UpdateBotInlineQuery, UpdateBotInlineSend, UpdateInlineBotCallbackQuery)
        }
        setattr(client, "workers", len(client.dispatcher.update_parsers))

        return client
