"""
Type annotated tasks and and overrides over invoke
"""

# pylint: disable=too-many-statements,duplicate-code

# pylint: disable=ungrouped-imports
import inspect
import os
import subprocess
import types
import warnings
from collections.abc import Callable, Iterable, Sequence
from enum import Enum
from functools import wraps
from typing import (
    Annotated,
    Any,
    Literal,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
    overload,
)

import setproctitle
from invoke.tasks import Call, Task, task as invoke_task
from invoke_toolkit.parser import ToolkitArgument
from invoke_toolkit.tasks.fields import UNSET, _DeferredField, _Field, is_field

from invoke_toolkit.context import ToolkitContext
from invoke_toolkit.tasks.cache import (
    CacheConfig,
    cached_task_wrapper,
    parse_cache_config,
)
from invoke_toolkit.tasks.types import _FileCompletionMarker

# Type alias for cache parameter
CacheParam = bool | dict | CacheConfig | None

F = TypeVar("F", bound=Callable[..., Any])


def _annotation_parts(annotation: Any) -> tuple[Any, tuple[Any, ...]]:
    """Return an annotation's runtime base type and Annotated metadata."""
    if get_origin(annotation) is Annotated:
        parts = get_args(annotation)
        if parts:
            return parts[0], tuple(parts[1:])
    return annotation, ()


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

            _, metadata = _annotation_parts(annotation)
            if metadata and isinstance(metadata[0], str):
                help_dict[param_name] = metadata[0]
    except (ValueError, TypeError):
        # If we can't extract, just return empty dict
        pass

    return help_dict


def _extract_completion_callbacks(func: Any) -> dict[str, Callable]:
    """
    Extract completion callbacks from Annotated types in function signature.

    Scans the function's parameters for Annotated types and extracts callable
    completion callbacks. This allows parameters to have dynamic completion.

    Skips the 'ctx' or 'c' parameter (Invoke Context) which Invoke doesn't allow help for.

    Args:
        func: The function to extract completion callbacks from

    Returns:
        Dictionary mapping parameter names to their completion callbacks
    """
    callbacks: dict[str, Callable] = {}

    try:
        sig = inspect.signature(func)
        for param_name, param in sig.parameters.items():
            # Skip 'self', 'ctx', 'c' and other special parameters
            if param_name.startswith("_") or param_name in ("ctx", "c"):
                continue

            annotation = param.annotation
            if annotation == inspect.Parameter.empty:
                continue

            _, annotation_metadata = _annotation_parts(annotation)
            for metadata in annotation_metadata:
                if callable(metadata) and not isinstance(metadata, type):
                    callbacks[param_name] = metadata
                    break
    except (ValueError, TypeError):
        # If we can't extract, just return empty dict
        pass

    return callbacks


def _extract_file_completion_markers(
    func: Any,
) -> dict[str, _FileCompletionMarker]:
    """
    Extract file completion markers from Annotated types and pathlib.Path hints.

    Scans the function's parameters for:
    1. Annotated types with _FileCompletionMarker metadata
    2. Raw pathlib.Path type hints (auto-detected for completion)

    Args:
        func: The function to extract file completion markers from

    Returns:
        Dictionary mapping parameter names to their file completion markers
    """
    from invoke_toolkit.tasks.types import (
        _FileCompletionMarker,
        _FilePathMarker,
        _FilePatternMarker,
        is_path_type,
    )

    markers: dict[str, _FileCompletionMarker] = {}

    try:
        sig = inspect.signature(func)
        for param_name, param in sig.parameters.items():
            # Skip 'self', 'ctx', 'c' and other special parameters
            if param_name.startswith("_") or param_name in ("ctx", "c"):
                continue

            annotation = param.annotation
            if annotation == inspect.Parameter.empty:
                continue

            base_annotation, metadata_items = _annotation_parts(annotation)
            for metadata in metadata_items:
                if isinstance(
                    metadata,
                    (_FileCompletionMarker, _FilePathMarker, _FilePatternMarker),
                ):
                    markers[param_name] = metadata
                    break
            else:
                if is_path_type(base_annotation):
                    markers[param_name] = _FileCompletionMarker()
    except (ValueError, TypeError):
        pass

    return markers


def _extract_literal_from_union(annotation: Any) -> tuple[Any, ...] | None:
    """
    Extract Literal values from a Union type (e.g., Literal["a", "b"] | None).

    Handles both typing.Union and types.UnionType (Python 3.10+ |).

    Args:
        annotation: The Union type annotation to extract from

    Returns:
        Tuple of literal values if found, None otherwise
    """
    if not _is_union_type(annotation):
        return None

    args = get_args(annotation)
    # Collect all literal values from any Literal types in the union
    all_literals = []
    for arg in args:
        if get_origin(arg) is Literal:
            all_literals.extend(get_args(arg))

    return tuple(all_literals) if all_literals else None


def _is_union_type(annotation: Any) -> bool:
    """
    Check if annotation is a Union type (typing.Union or types.UnionType).

    Handles both typing.Union and types.UnionType (Python 3.10+ |).

    Args:
        annotation: The annotation to check

    Returns:
        True if the annotation is a Union type
    """
    origin = get_origin(annotation)
    return origin is Union or isinstance(annotation, types.UnionType)


def _extract_enum_from_union(annotation: Any) -> type[Enum] | None:
    """
    Extract enum type from a Union type (e.g., Enum | None).

    Handles both typing.Union and types.UnionType (Python 3.10+ |).

    Args:
        annotation: The Union type annotation to extract from

    Returns:
        The Enum class if found, None otherwise
    """
    if not _is_union_type(annotation):
        return None

    args = get_args(annotation)
    for arg in args:
        try:
            if isinstance(arg, type) and issubclass(arg, Enum):
                return arg
        except TypeError:
            pass
    return None


def _extract_enum_params(func: Any) -> dict[str, type[Enum]]:
    """
    Extract enum type parameters from function signature.

    Handles both plain enum types and Annotated[Enum, ...].
    Also handles Union types where one of the args is an Enum (e.g., Enum | None).

    Args:
        func: The function to extract enum parameters from

    Returns:
        Dictionary mapping parameter names to their enum classes
    """
    enum_params: dict[str, type[Enum]] = {}

    try:
        sig = inspect.signature(func)
        for param_name, param in sig.parameters.items():
            if param_name.startswith("_") or param_name in ("ctx", "c"):
                continue

            annotation = param.annotation
            if annotation == inspect.Parameter.empty:
                continue
            annotation, _ = _annotation_parts(annotation)

            # Try direct enum type
            try:
                if isinstance(annotation, type) and issubclass(annotation, Enum):
                    enum_params[param_name] = annotation
                    continue
            except TypeError:
                pass

            # Try Union types (e.g., Enum | None)
            enum_from_union = _extract_enum_from_union(annotation)
            if enum_from_union is not None:
                enum_params[param_name] = enum_from_union
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
            annotation, _ = _annotation_parts(annotation)

            # Check for Literal or Union of Literals
            origin = get_origin(annotation)
            if origin is Literal:
                literal_params[param_name] = get_args(annotation)
            elif _is_union_type(annotation):
                # Try to extract Literal values from union (e.g., Literal["a", "b"] | None)
                literal_values = _extract_literal_from_union(annotation)
                if literal_values is not None:
                    literal_params[param_name] = literal_values
    except (ValueError, TypeError):
        pass

    return literal_params


def _extract_path_params(func: Any) -> dict[str, bool]:
    """
    Extract parameters that should be converted to pathlib.Path.

    Scans for parameters with Path type hints (including Optional[Path]).

    Args:
        func: The function to extract path parameters from

    Returns:
        Dictionary mapping parameter names to True if they should be Path objects
    """
    from invoke_toolkit.tasks.types import is_path_type

    path_params: dict[str, bool] = {}

    try:
        sig = inspect.signature(func)
        try:
            type_hints = get_type_hints(func, include_extras=True)
        except (NameError, TypeError):
            type_hints = {}
        for param_name, param in sig.parameters.items():
            if param_name.startswith("_") or param_name in ("ctx", "c"):
                continue

            annotation = type_hints.get(param_name, param.annotation)
            if annotation == inspect.Parameter.empty:
                continue

            # Check for Path type (handles Path, Optional[Path], Annotated[Path, ...])
            if is_path_type(annotation):
                path_params[param_name] = True

    except (ValueError, TypeError):
        pass

    return path_params


def _enum_choices_help(enum_class: type[Enum]) -> str:
    """Generate help text with available enum choices."""
    values = ", ".join(str(member.value) for member in enum_class)
    return f"Options: {values}"


def _literal_choices_help(literal_values: tuple[Any, ...]) -> str:
    """Generate help text with available literal choices."""
    values = ", ".join(str(v) for v in literal_values)
    return f"Options: {values}"


def _handle_validation_error(
    ctx: ToolkitContext | None,
    param_name: str,
    invalid_value: Any,
    valid_values: str,
) -> None:
    """
    Handle validation errors using rich output and exit.

    When context is available, exits with a rich error message.
    When context is not available, raises ValueError.

    Args:
        ctx: The ToolkitContext (optional)
        param_name: Name of the parameter that failed validation
        invalid_value: The invalid value that was provided
        valid_values: String representation of valid values

    Raises:
        ValueError: When context is not available
        SystemExit: When context is available (from ctx.rich_exit)
    """
    message = (
        f"[red]Invalid value[/red] '[yellow]{invalid_value}[/yellow]' "
        f"for parameter '[cyan]{param_name}[/cyan]'.\n"
        f"[green]Must be one of:[/green] {valid_values}"
    )
    if ctx is not None:
        ctx.rich_exit(message, exit_code=1)
    else:
        error_msg = (
            f"Invalid value '{invalid_value}' for {param_name}. "
            f"Must be one of: {valid_values}"
        )
        raise ValueError(error_msg)


class ToolkitTask(Task):
    """Task subclass that understands :func:`Field` signature defaults."""

    _field_definitions: dict[str, tuple[_Field, Any]]

    def fill_implicit_positionals(
        self, positional: Iterable[str] | None
    ) -> Sequence[str]:
        if positional is None:
            positional = [
                parameter.name
                for parameter in self.argspec(self.body).parameters.values()
                if parameter.default is inspect.Signature.empty
                or (is_field(parameter.default) and parameter.default.required)
            ]
        return tuple(positional)

    @staticmethod
    def _field_kind(annotation: Any) -> Any:
        """Derive Invoke's parser kind from a Field parameter annotation."""
        annotation, _ = _annotation_parts(annotation)
        if _is_union_type(annotation):
            members = [item for item in get_args(annotation) if item is not type(None)]
            if len(members) == 1:
                annotation = members[0]
        if get_origin(annotation) is Literal:
            values = get_args(annotation)
            return type(values[0]) if values else str
        try:
            if isinstance(annotation, type) and issubclass(annotation, Enum):
                return str
        except TypeError:
            pass
        from invoke_toolkit.tasks.types import is_path_type

        if is_path_type(annotation):
            return str
        return annotation if annotation in (str, int, float, list) else str

    def get_arguments(self, ignore_unknown_help: bool | None = None) -> list[Any]:
        sig = self.argspec(self.body)
        self._field_definitions = {}
        try:
            type_hints = get_type_hints(self.body, include_extras=True)
        except (NameError, TypeError):
            type_hints = {}
        taken_names = set(sig.parameters.keys())
        arguments: list[Any] = []
        for parameter in sig.parameters.values():
            default = parameter.default
            field = default if is_field(default) else None
            annotation = type_hints.get(parameter.name, parameter.annotation)
            effective_default = (
                inspect.Signature.empty
                if field is not None and field.required
                else default
            )
            opts = self.arg_opts(
                parameter.name,
                cast(Any, effective_default),
                taken_names,
            )
            if field is not None:
                kind = self._field_kind(annotation)
                if kind is bool or parameter.name in self.incrementable:
                    raise TypeError(
                        f"Field defaults are not supported for boolean or "
                        f"incrementable parameter '{parameter.name}'"
                    )
                if parameter.name in self.iterable:
                    raise TypeError(
                        f"Field defaults are not supported for iterable "
                        f"parameter '{parameter.name}'"
                    )
                opts["kind"] = kind
                self._field_definitions[parameter.name] = (field, annotation)
                if not field.required:
                    opts["default"] = _DeferredField(parameter.name)
            argument = ToolkitArgument(**opts)
            arguments.append(argument)
            taken_names.update(argument.names)
        if self.help and not ignore_unknown_help:
            raise ValueError(
                f"Help field was set for param(s) that don't exist: {list(self.help.keys())}"
            )
        for positional_name in reversed(list(self.positional)):
            for index, argument in enumerate(arguments):
                if argument.name == positional_name:
                    arguments.insert(0, arguments.pop(index))
                    break
        return arguments


def _field_context_value(context: ToolkitContext, parameter: str, field: _Field) -> Any:
    """Return an omitted Field's environment, config, or declared default."""
    environment_value = os.environ.get(f"INVOKE_{parameter.upper()}")
    if environment_value is not None:
        return environment_value
    configured_value = context.config.get(parameter, UNSET)
    if configured_value is not UNSET:
        return configured_value
    factory = field.default_factory
    return factory(context) if callable(factory) else field.default


def _materialize_field_arguments(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    field_definitions: dict[str, tuple[_Field, Any]],
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    """Replace omitted Field markers with their final runtime values."""
    signature = inspect.signature(func)
    bound = signature.bind(*args, **kwargs)
    bound.apply_defaults()
    context = bound.arguments.get(next(iter(signature.parameters)))
    if not isinstance(context, ToolkitContext):
        return bound.args, bound.kwargs
    try:
        type_hints = get_type_hints(func, include_extras=True)
    except (NameError, TypeError):
        type_hints = {}

    field_values: dict[str, Any] = {}
    annotations: dict[str, Any] = {}
    fields: dict[str, _Field] = {}
    for name, parameter in signature.parameters.items():
        current = bound.arguments.get(name)
        if isinstance(current, _DeferredField):
            field, fallback_annotation = field_definitions[current.parameter]
        elif is_field(current):
            field, fallback_annotation = current, parameter.annotation
        else:
            continue
        resolved_field = cast(_Field, field)
        if resolved_field.required:
            raise TypeError(f"Missing required task argument: '{name}'")
        field_values[name] = _field_context_value(context, name, resolved_field)
        annotation, _ = _annotation_parts(type_hints.get(name, fallback_annotation))
        annotations[name] = annotation
        fields[name] = resolved_field

    if field_values:
        from invoke_toolkit.field_resolvers import resolve_field_references

        bound.arguments.update(
            resolve_field_references(context, field_values, annotations, fields)
        )
    return bound.args, bound.kwargs


@overload
def task(
    func: F,
    *,
    name: str | None = None,
    default: bool | None = False,
    aliases: Sequence[str] | None = None,
    positional: Sequence[str] | None = None,
    optional: Sequence[str] | None = None,
    iterable: Sequence[str] | None = None,
    incrementable: Sequence[str] | None = None,
    bool_flags: tuple[str, ...] = (),
    autoprint: bool = False,
    help: dict[str, str] | None = None,
    pre: list[Callable[..., Any] | Call] | None = None,
    post: list[Callable[..., Any] | Call] | None = None,
    klass: type["ToolkitTask"] | None = ToolkitTask,
    proctitle: str | None = None,
    cache: CacheParam = None,
) -> F: ...


@overload
def task(
    func: None = None,
    *,
    name: str | None = None,
    default: bool | None = False,
    aliases: Sequence[str] | None = None,
    positional: Sequence[str] | None = None,
    optional: Sequence[str] | None = None,
    iterable: Sequence[str] | None = None,
    incrementable: Sequence[str] | None = None,
    bool_flags: tuple[str, ...] = (),
    autoprint: bool = False,
    help: dict[str, str] | None = None,
    pre: list[Callable[..., Any] | Call] | None = None,
    post: list[Callable[..., Any] | Call] | None = None,
    klass: type["ToolkitTask"] | None = ToolkitTask,
    proctitle: str | None = None,
    cache: CacheParam = None,
) -> Callable[[F], F]: ...


def task(  # pylint: disable=too-many-arguments,too-many-branches
    func: F | None = None,
    *,
    name: str | None = None,
    default: bool | None = False,
    aliases: Sequence[str] | None = None,
    positional: Sequence[str] | None = None,
    optional: Sequence[str] | None = None,
    iterable: Sequence[str] | None = None,
    incrementable: Sequence[str] | None = None,
    bool_flags: tuple[str, ...] = (),
    autoprint: bool = False,
    help: dict[str, str] | None = None,  # pylint: disable=redefined-builtin
    pre: list[Callable[..., Any] | Call] | None = None,
    post: list[Callable[..., Any] | Call] | None = None,
    klass: type["ToolkitTask"] | None = ToolkitTask,
    proctitle: str | None = None,
    cache: CacheParam = None,
) -> Any:
    """
    Decorator for Invoke tasks that preserves type hints and Context annotation.

    Supports all @task parameters while maintaining IDE/type checker support.

    Automatically merges parameter documentation from Annotated types with explicit help dict.
    Explicit help dict takes precedence over Annotated documentation.

    Enum and Literal parameters are auto-discovered and their choices added to help text.

    The proctitle parameter allows setting the process title while the task runs.
    When the task completes, the original process title is restored.

    Args:
        cache: Optional caching configuration for task results. Can be:
            - True: Enable caching with defaults
            - False/None: Disable caching (default)
            - dict: Enable with custom settings (ttl, key_prefix, ignore_args)
            - CacheConfig: Use a CacheConfig instance directly

            Cache location is computed from git repository root + platformdirs.
            Requires 'diskcache' package to be installed; gracefully degrades if not available.
            Cache hits/misses are logged when using -d (debug mode).

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

        # Setting process title
        @task(proctitle="Processing data")
        def process_task(ctx: Context) -> None:
            '''Task with custom process title.'''
            # Process title is "Processing data" while running
            do_processing()

        # Using caching - simple (no TTL)
        @task(cache=True)
        def expensive_task(ctx: Context, param: str) -> str:
            '''Results are cached across invocations.'''
            return do_expensive_computation(param)

        # Using caching with TTL (1 hour)
        @task(cache={"ttl": 3600})
        def cached_task(ctx: Context, name: str) -> dict:
            '''Results cached for 1 hour.'''
            return fetch_data(name)

        # Using caching with ignore_args (ctx excluded by default)
        @task(cache={"ttl": 600, "ignore_args": ["verbose"]})
        def cached_with_options(ctx: Context, query: str, verbose: bool = False) -> list:
            '''Cache key ignores verbose flag.'''
            return search(query, verbose=verbose)
    """

    def decorator(f: F) -> F:
        from pathlib import Path as PathlibPath

        # Extract enum, literal, and path params early for wrapper
        enum_params = _extract_enum_params(f)
        literal_params = _extract_literal_params(f)
        path_params = _extract_path_params(f)
        param_names = list(inspect.signature(f).parameters.keys())

        def prepare_call(args: tuple[Any, ...], kwargs: dict[str, Any]):
            ctx = args[0] if args and isinstance(args[0], ToolkitContext) else None
            args_list = list(args)
            for index, arg in enumerate(args_list):
                if index >= len(param_names):
                    continue
                param_name = param_names[index]
                if param_name in enum_params and isinstance(arg, str):
                    enum_class = enum_params[param_name]
                    try:
                        args_list[index] = enum_class(arg)
                    except ValueError as exc:
                        valid_values = ", ".join(
                            str(member.value) for member in enum_class
                        )
                        _handle_validation_error(ctx, param_name, arg, valid_values)
                        raise ValueError(valid_values) from exc
                if param_name in path_params and isinstance(arg, str):
                    args_list[index] = PathlibPath(arg)
            kwargs = dict(kwargs)
            for param_name, enum_class in enum_params.items():
                if param_name not in kwargs or not isinstance(kwargs[param_name], str):
                    continue
                try:
                    kwargs[param_name] = enum_class(kwargs[param_name])
                except ValueError as exc:
                    valid_values = ", ".join(str(member.value) for member in enum_class)
                    _handle_validation_error(
                        ctx, param_name, kwargs[param_name], valid_values
                    )
                    raise ValueError(valid_values) from exc
            for param_name in path_params:
                if param_name in kwargs and isinstance(kwargs[param_name], str):
                    kwargs[param_name] = PathlibPath(kwargs[param_name])
            for param_name, literal_values in literal_params.items():
                value = kwargs.get(param_name)
                if value is None and param_name in param_names:
                    index = param_names.index(param_name)
                    value = args_list[index] if index < len(args_list) else None
                if value is not None and value not in literal_values:
                    _handle_validation_error(
                        ctx, param_name, value, ", ".join(map(str, literal_values))
                    )
            for marker_name, marker in file_completion_markers.items():
                if not marker.exists:
                    continue
                value = kwargs.get(marker_name)
                if value is None and marker_name in param_names:
                    index = param_names.index(marker_name)
                    value = args_list[index] if index < len(args_list) else None
                if value is None:
                    continue
                path = PathlibPath(value)
                if not path.exists():
                    from invoke.exceptions import Exit

                    raise Exit(f"Path does not exist: {value}", code=1)
                if path.is_file() and not marker.file_okay:
                    from invoke.exceptions import Exit

                    raise Exit(f"Expected a directory, not a file: {value}", code=1)
                if path.is_dir() and not marker.dir_okay:
                    from invoke.exceptions import Exit

                    raise Exit(f"Expected a file, not a directory: {value}", code=1)
            return tuple(args_list), kwargs

        def set_title() -> tuple[str | None, str | None, str | None]:
            if proctitle is None:
                return None, None, None
            previous = setproctitle.getproctitle()
            previous_tmux = None
            if os.environ.get("TMUX"):
                result = subprocess.run(
                    ["tmux", "display-message", "-p", "#W"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode == 0:
                    previous_tmux = result.stdout.strip()
                subprocess.run(["tmux", "rename-window", proctitle], check=False)
            setproctitle.setproctitle(proctitle)
            return previous, previous_tmux, proctitle

        def restore_title(
            previous_state: tuple[str | None, str | None, str | None],
        ) -> None:
            previous, previous_tmux, _ = previous_state
            if previous is None:
                return
            setproctitle.setproctitle(previous)
            if previous_tmux is not None:
                subprocess.run(["tmux", "rename-window", previous_tmux], check=False)

        if inspect.iscoroutinefunction(f):

            @wraps(f)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                args, kwargs = prepare_call(args, kwargs)
                previous = set_title()
                try:
                    return await f(*args, **kwargs)
                finally:
                    restore_title(previous)

            wrapper = async_wrapper
        else:

            @wraps(f)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                args, kwargs = prepare_call(args, kwargs)
                previous = set_title()
                try:
                    return f(*args, **kwargs)
                finally:
                    restore_title(previous)

            wrapper = sync_wrapper

        # Preserve the type hints on the wrapper
        wrapper.__annotations__ = f.__annotations__

        # Extract completion callbacks
        completion_callbacks = _extract_completion_callbacks(f)

        # Extract file completion markers
        file_completion_markers = _extract_file_completion_markers(f)

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
            # Normalize a name to invoke's canonical form (underscores → hyphens).
            effective_name = (name or getattr(f, "__name__", "")).replace("_", "-")
            filtered_aliases = [
                a for a in aliases if a.replace("_", "-") != effective_name
            ]
            skipped = set(aliases) - set(filtered_aliases)
            if skipped:
                warnings.warn(
                    f"Task '{effective_name}': alias(es) {sorted(skipped)!r} "
                    "match the task name and will be ignored to prevent a "
                    "RecursionError at runtime.",
                    UserWarning,
                    stacklevel=2,
                )
            if filtered_aliases:
                task_kwargs["aliases"] = filtered_aliases
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

        # Cache receives final materialized values, not Field markers/references.
        cache_config = parse_cache_config(cache)
        validation_wrapper = wrapper
        if cache_config is not None:
            execution_wrapper = cached_task_wrapper(validation_wrapper, cache_config)
        else:
            execution_wrapper = validation_wrapper

        task_decorated: Any = None

        def field_definitions() -> dict[str, tuple[_Field, Any]]:
            if task_decorated is None:
                return {}
            return getattr(task_decorated, "_field_definitions", {})

        if inspect.iscoroutinefunction(execution_wrapper):

            @wraps(f)
            async def async_field_wrapper(*args: Any, **kwargs: Any) -> Any:
                from invoke_toolkit.field_resolvers import FieldCleanupManager

                context = (
                    args[0] if args and isinstance(args[0], ToolkitContext) else None
                )
                if context is None:
                    materialized_args, materialized_kwargs = (
                        _materialize_field_arguments(
                            f, args, kwargs, field_definitions()
                        )
                    )
                    return await execution_wrapper(
                        *materialized_args, **materialized_kwargs
                    )
                owner = not hasattr(context, "_field_cleanup")
                if owner:
                    context._field_cleanup = FieldCleanupManager()
                failed = False
                try:
                    with context._field_cleanup.task_scope():
                        materialized_args, materialized_kwargs = (
                            _materialize_field_arguments(
                                f, args, kwargs, field_definitions()
                            )
                        )
                        return await execution_wrapper(
                            *materialized_args, **materialized_kwargs
                        )
                except BaseException:
                    failed = True
                    raise
                finally:
                    if owner:
                        context._field_cleanup.close_pipeline(failed)
                        del context._field_cleanup

            field_wrapper = async_field_wrapper
        else:

            @wraps(f)
            def sync_field_wrapper(*args: Any, **kwargs: Any) -> Any:
                from invoke_toolkit.field_resolvers import FieldCleanupManager

                context = (
                    args[0] if args and isinstance(args[0], ToolkitContext) else None
                )
                if context is None:
                    materialized_args, materialized_kwargs = (
                        _materialize_field_arguments(
                            f, args, kwargs, field_definitions()
                        )
                    )
                    return execution_wrapper(*materialized_args, **materialized_kwargs)
                owner = not hasattr(context, "_field_cleanup")
                if owner:
                    context._field_cleanup = FieldCleanupManager()
                failed = False
                try:
                    with context._field_cleanup.task_scope():
                        materialized_args, materialized_kwargs = (
                            _materialize_field_arguments(
                                f, args, kwargs, field_definitions()
                            )
                        )
                        return execution_wrapper(
                            *materialized_args, **materialized_kwargs
                        )
                except BaseException:
                    failed = True
                    raise
                finally:
                    if owner:
                        context._field_cleanup.close_pipeline(failed)
                        del context._field_cleanup

            field_wrapper = sync_field_wrapper

        field_wrapper.__signature__ = inspect.signature(f)  # type: ignore[attr-defined]
        task_decorated = invoke_task(field_wrapper, klass=klass, **task_kwargs)

        task_decorated._field_definitions = {}  # type: ignore[attr-defined]
        for parameter in inspect.signature(f).parameters.values():
            if is_field(parameter.default):
                task_decorated._field_definitions[parameter.name] = (  # type: ignore[attr-defined]
                    parameter.default,
                    parameter.annotation,
                )
        # Store reference to original function
        task_decorated.__wrapped__ = f  # type: ignore[attr-defined]
        # Store completion callbacks for use in completion system
        task_decorated._completion_callbacks = completion_callbacks  # pylint: disable=protected-access  # type: ignore[attr-defined]
        # Store file completion markers for use in completion system
        task_decorated._file_completion_markers = file_completion_markers  # pylint: disable=protected-access  # type: ignore[attr-defined]

        return cast(F, task_decorated)

    # Support both @task and @task(...) syntax
    if func is not None:
        return decorator(func)
    return decorator


class ToolkitCall(Call):
    def make_context(
        self, config: Any, core_parse_result: Any = None
    ) -> ToolkitContext:
        """Generate a toolkit context with the parser remainder."""
        remainder = core_parse_result.remainder if core_parse_result is not None else ""
        return ToolkitContext(config=config, remainder=remainder)


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
