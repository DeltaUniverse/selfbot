import asyncio
import logging

import httpx

from .dispatcher import Dispatcher
from .extender import Extender
from .telegram import Telegram


class Selfbot(Dispatcher, Extender, Telegram):
    def __init__(self, config: dict) -> None:
        self.config = config

        self.log = logging.getLogger("Selfbot")

        self.loop = asyncio.get_event_loop()
        self.http = httpx.AsyncClient()

        super().__init__()

    @classmethod
    async def launch(
        cls, config: dict, *, loop: asyncio.AbstractEventLoop = None
    ) -> "Selfbot":
        if loop:
            asyncio.set_event_loop(loop)

        selfbot = cls(config)

        try:
            await selfbot.run()
        finally:
            if loop and not loop.is_closed():
                loop.stop()

        return selfbot

    async def stop(self) -> None:
        await asyncio.gather(self.app.stop(), self.bot.stop(), self.http.aclose())
