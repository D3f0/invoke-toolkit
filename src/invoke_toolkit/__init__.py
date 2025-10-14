"""Package namespace imports"""

from functools import wraps
from typing import Any, Callable, Optional, TypeVar, cast

from invoke import task as invoke_task

from invoke_toolkit.context import InvokeToolkitContext as Context  # noqa: F401

F = TypeVar("F", bound=Callable[..., Any])

__all__ = ["task", "Context"]


F = TypeVar("F", bound=Callable[..., Any])


def task(  # pylint: disable=too-many-arguments
    func: Optional[F] = None,
    *,
    name: Optional[str] = None,
    default: Optional[bool] = False,
    aliases: tuple[str, ...] = (),
    positional: tuple[str, ...] = (),
    optional: tuple[str, ...] = (),
    iterable: tuple[str, ...] = (),
    incrementable: tuple[str, ...] = (),
    bool_flags: tuple[str, ...] = (),
    autoprint: bool = False,
    help: Optional[dict[str, str]] = None,  # pylint: disable=redefined-builtin
    pre: Optional[list[Callable[..., Any]]] = None,
    post: Optional[list[Callable[..., Any]]] = None,
) -> Callable[[F], F]:
    """
    Decorator for Invoke tasks that preserves type hints and Context annotation.

    Supports all @task parameters while maintaining IDE/type checker support.

    Usage:
        @task
        def my_task(c: Context, name: str, count: int = 5) -> None:
            '''Do something with name and count.'''
            pass

        @task(autoprint=True, help={"name": "The target name"})
        def another_task(c: Context, name: str) -> None:
            return "result"
    """

    def decorator(f: F) -> F:
        # Create a wrapper that Invoke can work with
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return f(*args, **kwargs)

        # Preserve the type hints on the wrapper
        wrapper.__annotations__ = f.__annotations__

        # Build task decorator kwargs
        task_kwargs: dict[str, Any] = {}

        if name is not None:
            task_kwargs["name"] = name
        if aliases:
            task_kwargs["aliases"] = aliases
        if positional:
            task_kwargs["positional"] = positional
        if optional:
            task_kwargs["optional"] = optional
        if iterable:
            task_kwargs["iterable"] = iterable
        if incrementable:
            task_kwargs["incrementable"] = incrementable
        if bool_flags:
            task_kwargs["bool_flags"] = bool_flags
        if autoprint:
            task_kwargs["autoprint"] = autoprint
        if help is not None:
            task_kwargs["help"] = help
        if pre is not None:
            task_kwargs["pre"] = pre
        if post is not None:
            task_kwargs["post"] = post
        if default is not None:
            task_kwargs["default"] = default

        # Apply the Invoke @task decorator
        task_decorated = invoke_task(wrapper, **task_kwargs)

        # Store reference to original function
        task_decorated.__wrapped__ = f

        return cast(F, task_decorated)

    # Support both @typed_task and @typed_task(...) syntax
    if func is not None:
        return decorator(func)
    return decorator
