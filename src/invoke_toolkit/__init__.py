from typing import Callable

from invoke import Task
from typing_extensions import Any, ParamSpec, Type, TypeVar, overload
from invoke_toolkit.context import InvokeToolkitContext as Context  # noqa: F401

P = ParamSpec("P")
R = TypeVar("R")


@overload
def task(func: Callable[P, R]) -> Task[Callable[P, R]]: ...


@overload
def task(
    *args: Any, **kwargs: Any
) -> Callable[[Callable[P, R]], Task[Callable[P, R]]]: ...


def task(*args: Any, **kwargs: Any) -> Any:
    """
    Annotated decorator for Invoke tasks.

    If used without arguments, returns a Task-wrapped function with preserved signature.
    If used with arguments, returns a decorator preserving the signature.
    """
    klass: Type[Task] = kwargs.pop("klass", Task)
    if len(args) == 1 and callable(args[0]) and not isinstance(args[0], Task):
        return klass(args[0], **kwargs)
    if args:
        if "pre" in kwargs:
            raise TypeError("May not give *args and 'pre' kwarg simultaneously!")
        kwargs["pre"] = args

    def inner(body: Callable[P, R]) -> Task[Callable[P, R]]:
        _task = klass(body, **kwargs)
        return _task

    return inner
