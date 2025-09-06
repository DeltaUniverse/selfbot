import abc
import asyncio
import bisect

from pyrogram.types import Update

from selfbot.listener import Listener
from selfbot.module import Module


class Dispatcher(abc.ABC):
    def __init__(self, **kwargs) -> None:
        self.listeners = {}

        super().__init__(**kwargs)

    async def dispatch(self, event: str, *args, **kwargs) -> None:
        listeners = self.listeners.get(event)

        if not listeners:
            return

        tasks = set()

        for listener in listeners:
            if listener.filters and args:
                update = args[0]

                if isinstance(update, Update):
                    match = await listener.filters(update._client, update)

                    if not match:
                        continue

            tasks.add(self.loop.create_task(listener.func(*args, **kwargs)))

        if tasks:
            await asyncio.wait(tasks)

    def registers(self, mod: "Module") -> None:
        for event, func in mod_funcs(mod, "on_"):
            done = False

            try:
                self.register(
                    mod,
                    func,
                    event,
                    filters=getattr(func, "filters", None),
                    priority=getattr(func, "priority", 100),
                )

                done = True

            finally:
                if not done:
                    self.unregisters(mod)

    def unregisters(self, mod: "Module") -> None:
        slots = []

        for event, listeners in self.listeners.items():
            for listener in listeners:
                if listener.mod == mod:
                    slots.append(listener)

        for listener in slots:
            self.unregister(listener)

    def register(
        self, mod: type, func: callable, event: str, *, filters=None, priority=100
    ) -> None:
        if event not in self.listeners:
            self.listeners[event] = []

        bisect.insort(
            self.listeners[event], Listener(mod, func, event, filters, priority)
        )

        self.updates()

    def unregister(self, listener: "Listener") -> None:
        self.listeners[listener.event].remove(listener)

        if not self.listeners[listener.event]:
            del self.listeners[listener.event]

        self.updates()


def mod_funcs(mod: "Module", prefix: str) -> list:
    res = []

    for attr in dir(mod):
        if attr.startswith(prefix):
            func = getattr(mod, attr)

            if callable(func):
                res.append((attr[len(prefix) :], func))

    return res
