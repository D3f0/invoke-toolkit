"""
Type annotated tasks and and overrides over invoke
"""

# pylint: disable=too-many-statements

import inspect
from enum import Enum
from functools import wraps
from typing import (
    Annotated,
    Any,
    Callable,
    Literal,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
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


def _extract_enum_params(func: Any) -> dict[str, Type[Enum]]:
    """
    Extract enum type parameters from function signature.

    Handles both plain enum types and Annotated[Enum, ...].

    Args:
        func: The function to extract enum parameters from

    Returns:
        Dictionary mapping parameter names to their enum classes
    """
    enum_params: dict[str, Type[Enum]] = {}

    try:
        sig = inspect.signature(func)
        for param_name, param in sig.parameters.items():
            if param_name.startswith("_") or param_name in ("ctx", "c"):
                continue

            annotation = param.annotation
            if annotation == inspect.Parameter.empty:
                continue

            # Check if it's an Annotated type and extract the actual type
            if get_origin(annotation) is Annotated:
                args = get_args(annotation)
                if args:
                    annotation = args[0]

            try:
                if isinstance(annotation, type) and issubclass(annotation, Enum):
                    enum_params[param_name] = annotation
            except TypeError:
                pass
    except (ValueError, TypeError):
        pass

    return enum_params


def _extract_literal_params(func: Any) -> dict[str, tuple[Any, ...]]:
    """
    Extract Literal type parameters from function signature.

    Handles both plain Literal types and Annotated[Literal[...], ...].

    Args:
        func: The function to extract literal parameters from

    Returns:
        Dictionary mapping parameter names to their literal values
    """
    literal_params: dict[str, tuple[Any, ...]] = {}

    try:
        sig = inspect.signature(func)
        for param_name, param in sig.parameters.items():
            if param_name.startswith("_") or param_name in ("ctx", "c"):
                continue

            annotation = param.annotation
            if annotation == inspect.Parameter.empty:
                continue

            # Check if it's an Annotated type and extract the actual type
            if get_origin(annotation) is Annotated:
                args = get_args(annotation)
                if args:
                    annotation = args[0]

            # Check for Literal or Union of Literals
            origin = get_origin(annotation)
            if origin is Literal:
                literal_params[param_name] = get_args(annotation)
            elif origin is Union:
                # Check if all args are Literals
                args = get_args(annotation)
                if all(get_origin(arg) is Literal for arg in args):
                    # Flatten all literal values
                    all_literals = tuple(val for arg in args for val in get_args(arg))
                    if all_literals:
                        literal_params[param_name] = all_literals
    except (ValueError, TypeError):
        pass

    return literal_params


def _enum_choices_help(enum_class: Type[Enum]) -> str:
    """Generate help text with available enum choices."""
    values = ", ".join(str(member.value) for member in enum_class)
    return f"Options: {values}"


def _literal_choices_help(literal_values: tuple[Any, ...]) -> str:
    """Generate help text with available literal choices."""
    values = ", ".join(str(v) for v in literal_values)
    return f"Options: {values}"


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

    Enum and Literal parameters are auto-discovered and their choices added to help text.

    Usage:
        @task
        def my_task(c: Context, name: str, count: int = 5) -> None:
            '''Do something with name and count.'''
            pass

        @task(autoprint=True, help={"name": "The target name"})
        def another_task(c: Context, name: str) -> None:
            return "result"

        # Using enums for parameter choices
        from enum import Enum

        class Color(str, Enum):
            RED = "red"
            GREEN = "green"

        @task
        def color_task(ctx: Context, color: Color) -> None:
            '''Choices auto-discovered from enum.'''
            print(f"Selected: {color.value}")

        # Using Literal types
        @task
        def literal_task(ctx: Context, level: Literal["debug", "info", "error"]) -> None:
            '''Literal options in help.'''
            print(f"Level: {level}")
    """

    def decorator(f: F) -> F:
        # Extract enum and literal params early for wrapper
        enum_params = _extract_enum_params(f)
        literal_params = _extract_literal_params(f)
        param_names = list(inspect.signature(f).parameters.keys())

        # Create a wrapper that Invoke can work with
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Convert string enum values to enum instances with validation
            if enum_params:
                # Convert positional args
                args_list = list(args)
                for i, arg in enumerate(args_list):
                    if i < len(param_names):
                        param_name = param_names[i]
                        if param_name in enum_params and isinstance(arg, str):
                            enum_class = enum_params[param_name]
                            try:
                                args_list[i] = enum_class(arg)
                            except ValueError as exc:
                                valid_values = ", ".join(
                                    str(m.value) for m in enum_class
                                )
                                raise ValueError(
                                    f"Invalid value '{arg}' for {param_name}. "
                                    f"Must be one of: {valid_values}"
                                ) from exc
                args = tuple(args_list)

                # Convert kwargs
                for param_name, enum_class in enum_params.items():
                    if param_name in kwargs and isinstance(kwargs[param_name], str):
                        try:
                            kwargs[param_name] = enum_class(kwargs[param_name])
                        except ValueError as exc:
                            valid_values = ", ".join(str(m.value) for m in enum_class)
                            raise ValueError(
                                f"Invalid value '{kwargs[param_name]}' for {param_name}. "
                                f"Must be one of: {valid_values}"
                            ) from exc

            # Validate literal values
            if literal_params:
                for param_name, literal_values in literal_params.items():
                    # Check kwargs
                    if param_name in kwargs:
                        if kwargs[param_name] not in literal_values:
                            raise ValueError(
                                f"Invalid value '{kwargs[param_name]}' for {param_name}. "
                                f"Must be one of: {', '.join(str(v) for v in literal_values)}"
                            )

                    # Check positional args
                    for i, param in enumerate(param_names):
                        if param == param_name and i < len(args):
                            if args[i] not in literal_values:
                                raise ValueError(
                                    f"Invalid value '{args[i]}' for {param_name}. "
                                    f"Must be one of: {', '.join(str(v) for v in literal_values)}"
                                )

            return f(*args, **kwargs)

        # Preserve the type hints on the wrapper
        wrapper.__annotations__ = f.__annotations__

        # Extract all help sources
        annotated_help = _extract_annotated_help(f)
        enum_help = {
            name: _enum_choices_help(enum_class)
            for name, enum_class in enum_params.items()
        }
        literal_help = {
            name: _literal_choices_help(literal_values)
            for name, literal_values in literal_params.items()
        }

        # Merge help: enums/literals < annotated < explicit (explicit wins)
        # Prepend options to annotated help
        merged_help = enum_help.copy()
        merged_help.update(literal_help)
        for param_name, doc in annotated_help.items():
            if param_name in merged_help:
                # Prepend options to annotated doc
                merged_help[param_name] = f"{merged_help[param_name]}. {doc}"
            else:
                merged_help[param_name] = doc
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
        task_decorated = invoke_task(wrapper, klass=klass, **task_kwargs)

        # Store reference to original function
        task_decorated.__wrapped__ = f  # type: ignore[attr-defined]

        return cast(F, task_decorated)

    # Support both @task and @task(...) syntax
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
