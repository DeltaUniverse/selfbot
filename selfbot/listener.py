class Listener:
    def __init__(
        self, mod: type, func: callable, event: str, filters: callable, priority: int
    ) -> None:
        self.mod = mod
        self.func = func
        self.event = event
        self.filters = filters
        self.priority = priority

    def __lt__(self, other: "Listener") -> bool:
        return self.priority < other.priority


def handler(filters: callable, priority: int) -> callable:
    def wrapper(func: callable) -> callable:
        setattr(func, "filters", filters)
        setattr(func, "priority", priority)

        return func

    return wrapper
