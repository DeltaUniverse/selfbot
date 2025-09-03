import abc
import inspect

from selfbot.module import Module, ModuleExists
from selfbot.modules import submods


class Extender(abc.ABC):
    def __init__(self, **kwargs) -> None:
        self.modules = {}

        super().__init__(**kwargs)

    def load(self, mod: type) -> None:
        if mod.name in self.modules:
            raise ModuleExists(type(self.modules[mod.name]), mod)

        new = mod(self)

        try:
            self.registers(new)
        except Exception as e:
            self.unregisters(new)
            self.log.error(str(e))
        else:
            self.log.info("'%s' Loaded", mod.name)
        finally:
            self.modules[mod.name] = new

    def loads(self) -> None:
        for submod in submods:
            for attr in dir(submod):
                mod = getattr(submod, attr)

                if (
                    inspect.isclass(mod)
                    and issubclass(mod, Module)
                    and mod is not Module
                ):
                    self.load(mod)

    def unload(self, mod: type) -> None:
        try:
            self.unregisters(mod)
        except Exception as e:
            self.log.error(str(e))
        else:
            self.log.info("'%s' Unloaded", mod.name)
        finally:
            del self.modules[type(mod).name]

    def unloads(self) -> None:
        for key in list(self.modules.keys()):
            self.unload(self.modules[key])
