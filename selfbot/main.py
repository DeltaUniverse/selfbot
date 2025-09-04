import asyncio
import logging

import aiorun
import dotenv

from .core import Selfbot

logging.basicConfig(
    format="%(asctime)s [%(levelname).1s] %(name)s: %(message)s",
    datefmt="%b %-d, %-I:%M %p",
    level=logging.INFO,
)

for lib in ["pyrogram", "httpx"]:
    logging.getLogger(lib).setLevel(logging.ERROR)


def run() -> None:
    config = dotenv.dotenv_values()

    try:
        import uvloop
    except ImportError:
        pass
    else:
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    aiorun.logger.disabled = True
    aiorun.run(Selfbot.launch(config, loop=loop), loop=loop)
