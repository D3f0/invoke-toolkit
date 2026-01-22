"""
Type annotated tasks and and overrides over invoke
"""

import inspect
from functools import wraps
from typing import (
    Annotated,
    Any,
    Callable,
    Optional,
    Sequence,
    Type,
    TypeVar,
    cast,
    get_args,
    get_origin,
    overload,
)

from invoke import task as invoke_task
from invoke.tasks import Call, Task

from invoke_toolkit.context import ToolkitContext

F = TypeVar("F", bound=Callable[..., Any])


def _extract_annotated_help(func: Any) -> dict[str, str]:
    """
    Extract parameter documentation from Annotated types in function signature.

    Scans the function's parameters for Annotated types and extracts their
    documentation strings. This allows parameters to be self-documenting
    without requiring a separate help dict.

    Skips the 'ctx' or 'c' parameter (Invoke Context) which Invoke doesn't allow help for.

    Args:
        func: The function to extract documentation from

    Returns:
        Dictionary mapping parameter names to their documentation strings from Annotated types
    """
    help_dict: dict[str, str] = {}

    try:
        sig = inspect.signature(func)
        for param_name, param in sig.parameters.items():
            # Skip 'self', 'ctx', 'c' and other special parameters
            if param_name.startswith("_") or param_name in ("ctx", "c"):
                continue

            annotation = param.annotation
            if annotation == inspect.Parameter.empty:
                continue

            # Check if it's an Annotated type
            if get_origin(annotation) is Annotated:
                args = get_args(annotation)
                # Annotated[type, doc, ...] - doc is the second argument
                if len(args) > 1 and isinstance(args[1], str):
                    help_dict[param_name] = args[1]
    except (ValueError, TypeError):
        # If we can't extract, just return empty dict
        pass

    return help_dict


class ToolkitTask(Task): ...


@overload
def task(
    func: F,
    *,
    name: Optional[str] = None,
    default: Optional[bool] = False,
    aliases: Optional[Sequence[str]] = None,
    positional: Optional[Sequence[str]] = None,
    optional: Optional[Sequence[str]] = None,
    iterable: Optional[Sequence[str]] = None,
    incrementable: Optional[Sequence[str]] = None,
    bool_flags: tuple[str, ...] = (),
    autoprint: bool = False,
    help: Optional[dict[str, str]] = None,
    pre: Optional[list[Callable[..., Any]]] = None,
    post: Optional[list[Callable[..., Any]]] = None,
    klass: Optional[Type["ToolkitTask"]] = ToolkitTask,
) -> F: ...


@overload
def task(
    func: None = None,
    *,
    name: Optional[str] = None,
    default: Optional[bool] = False,
    aliases: Optional[Sequence[str]] = None,
    positional: Optional[Sequence[str]] = None,
    optional: Optional[Sequence[str]] = None,
    iterable: Optional[Sequence[str]] = None,
    incrementable: Optional[Sequence[str]] = None,
    bool_flags: tuple[str, ...] = (),
    autoprint: bool = False,
    help: Optional[dict[str, str]] = None,
    pre: Optional[list[Callable[..., Any]]] = None,
    post: Optional[list[Callable[..., Any]]] = None,
    klass: Optional[Type["ToolkitTask"]] = ToolkitTask,
) -> Callable[[F], F]: ...


def task(  # pylint: disable=too-many-arguments,too-many-branches
    func: Optional[F] = None,
    *,
    name: Optional[str] = None,
    default: Optional[bool] = False,
    aliases: Optional[Sequence[str]] = None,
    positional: Optional[Sequence[str]] = None,
    optional: Optional[Sequence[str]] = None,
    iterable: Optional[Sequence[str]] = None,
    incrementable: Optional[Sequence[str]] = None,
    bool_flags: tuple[str, ...] = (),
    autoprint: bool = False,
    help: Optional[dict[str, str]] = None,  # pylint: disable=redefined-builtin
    pre: Optional[list[Callable[..., Any]]] = None,
    post: Optional[list[Callable[..., Any]]] = None,
    klass: Optional[Type["ToolkitTask"]] = ToolkitTask,
) -> Any:
    """
    Decorator for Invoke tasks that preserves type hints and Context annotation.

    Supports all @task parameters while maintaining IDE/type checker support.

    Automatically merges parameter documentation from Annotated types with explicit help dict.
    Explicit help dict takes precedence over Annotated documentation.

    Usage:
        @task
        def my_task(c: Context, name: str, count: int = 5) -> None:
            '''Do something with name and count.'''
            pass

        @task(autoprint=True, help={"name": "The target name"})
        def another_task(c: Context, name: str) -> None:
            return "result"

        # Using Annotated for self-documenting parameters
        @task
        def documented_task(
            ctx: Context,
            name: Annotated[str, "The target name"],
            count: Annotated[int, "Number of iterations"] = 5,
        ) -> None:
            '''Task with Annotated parameter documentation.'''
            pass

        # Explicit help dict overrides Annotated documentation
        @task(help={"name": "Override annotation doc"})
        def override_task(
            ctx: Context,
            name: Annotated[str, "Original annotation doc"],
        ) -> None:
            pass
    """

    def decorator(f: F) -> F:
        # Create a wrapper that Invoke can work with
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return f(*args, **kwargs)

        # Preserve the type hints on the wrapper
        wrapper.__annotations__ = f.__annotations__

        # Extract documentation from Annotated types
        annotated_help = _extract_annotated_help(f)

        # Merge explicit help with Annotated documentation
        # Explicit help takes precedence
        merged_help = annotated_help.copy()
        if help is not None:
            merged_help.update(help)

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
        if merged_help:
            task_kwargs["help"] = merged_help
        if pre is not None:
            task_kwargs["pre"] = pre
        if post is not None:
            task_kwargs["post"] = post
        if default is not None:
            task_kwargs["default"] = default

        # Apply the Invoke @task decorator
        task_decorated = invoke_task(wrapper, **task_kwargs)

        # Store reference to original function
        task_decorated.__wrapped__ = f  # type: ignore[attr-defined]

        return cast(F, task_decorated)

    # Support both @typed_task and @typed_task(...) syntax
    if func is not None:
        return decorator(func)
    return decorator


class ToolkitCall(Call):
    def make_context(self, config):
        """Generates the Context for the task"""
        return ToolkitContext(config=config)


def call(task_: "Task", *args: Any, **kwargs: Any) -> "Call":
    """
    Describes execution of a `.Task`, typically with pre-supplied arguments.

    Useful for setting up :ref:`pre/post task invocations
    <parameterizing-pre-post-tasks>`. It's actually just a convenient wrapper
    around the `.Call` class, which may be used directly instead if desired.

    For example, here's two build-like tasks that both refer to a ``setup``
    pre-task, one with no baked-in argument values (and thus no need to use
    `.call`), and one that toggles a boolean flag::

        @task
        def setup(c, clean=False):
            if clean:
                c.run("rm -rf target")
            # ... setup things here ...
            c.run("tar czvf target.tgz target")

        @task(pre=[setup])
        def build(c):
            c.run("build, accounting for leftover files...")

        @task(pre=[call(setup, clean=True)])
        def clean_build(c):
            c.run("build, assuming clean slate...")

    Please see the constructor docs for `.Call` for details - this function's
    ``args`` and ``kwargs`` map directly to the same arguments as in that
    method.

    .. versionadded:: 1.0
    """
    return ToolkitCall(task_, args=args, kwargs=kwargs)
