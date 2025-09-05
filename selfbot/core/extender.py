import abc
import inspect

from selfbot.module import Module, ModuleExists
from selfbot.modules import submods


class Extender(abc.ABC):
    def __init__(self, **kwargs) -> None:
        self.modules = {}

        super().__init__(**kwargs)

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

    def unloads(self) -> None:
        for key in list(self.modules.keys()):
            self.unload(self.modules[key])

    def load(self, mod: "Module") -> None:
        if mod.name in self.modules:
            raise ModuleExists(type(self.modules[mod.name]), mod)

        new = mod(self)

        try:
            self.registers(new)
        except Exception as e:
            self.unregisters(new)
            self.logger.error(str(e))
        else:
            self.logger.info(f"{mod.name} Loaded")
        finally:
            self.modules[mod.name] = new

    def unload(self, mod: "Module") -> None:
        try:
            self.unregisters(mod)
        except Exception as e:
            self.logger.error(str(e))
        else:
            self.logger.info(f"{mod.name} Unloaded")
        finally:
            del self.modules[type(mod).name]
