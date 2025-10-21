from typing import TypeVar, Callable, Any
from functools import wraps

T = TypeVar("T")


def singleton(cls: type[T]) -> Callable[..., T]:
    """
    Decorator that converts a class into a singleton.

    For testing it adds a _reset method.

    Args:
        cls: The class to make a singleton

    Returns:
        A function that returns the singleton instance
    """
    instances: dict[type[T], T] = {}

    @wraps(cls)
    def get_instance(*args: Any, **kwargs: Any) -> T:
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    def reset() -> None:
        """Reset the singleton instance"""
        instances.pop(cls, None)

    get_instance.reset = reset
    return get_instance
