from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from selfbot.core import Selfbot


class Module:
    name: str = "Unnamed"

    def __init__(self, client: "Selfbot") -> None:
        self.client = client


class ModuleError(Exception):
    pass


class ModuleExists(ModuleError):
    def __init__(self, old: "Module", new: "Module") -> None:
        self.old = old
        self.new = new

        super().__init__(f"'{self.old.name}' Exists")
