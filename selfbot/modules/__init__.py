import importlib
import pathlib
import pkgutil

parents = [str(pathlib.Path(__file__).parent)]
submods = [
    importlib.import_module(f".{info.name}", __name__)
    for info in pkgutil.iter_modules(parents)
]

try:
    again: bool

    if again:
        for module in submods:
            importlib.reload(module)

except NameError:
    again = True
