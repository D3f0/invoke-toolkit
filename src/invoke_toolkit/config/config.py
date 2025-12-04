"""
Custom config class passed in every context class as .config
This module defines some functions/callables
"""

import inspect as frame_inspect
from typing import TYPE_CHECKING, Any, Dict, NoReturn, Optional, TypeVar, overload

from invoke.config import Config
from invoke.util import debug

from ..runners.rich import NoStdoutRunner

if TYPE_CHECKING:
    from invoke_toolkit.context import ToolkitContext


# TypeVar for return type
T = TypeVar("T")


def deep_merge(dict1, dict2):
    """Recursively merge dict2 into dict1"""
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


class ToolkitConfig(Config):
    """
    Config object used for resolving ctx attributes and functions
    such as .cd, .run, etc.

    To create a custom config class you can do the following

    ```python
    class MyConfig(Config, prefix="custom", file_prefix="file_", env_prefix="ENV_"):
        pass

    ```
    """

    def __init_subclass__(
        cls,
        prefix: Optional[str] = None,
        file_prefix: Optional[str] = None,
        env_prefix: Optional[str] = None,
        extra_defaults: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        super().__init_subclass__(**kwargs)
        if prefix is not None:
            cls.prefix = prefix
        if file_prefix is not None:
            cls.file_prefix = file_prefix
        if env_prefix is not None:
            cls.env_prefix = env_prefix
        if extra_defaults:
            cls.extra_defaults = extra_defaults
        else:
            cls.extra_defaults = None

    extra_defaults: Optional[Dict[str, Any]]

    # This method is a static method in the super class
    # but it's converted to class method here, so we can
    # a reference to the attribute set by __init_subclass__
    @classmethod
    def global_defaults(cls) -> Dict[str, Any]:
        """
        Return the core default settings for Invoke.

        Generally only for use by `.Config` internals. For descriptions of
        these values, see :ref:`default-values`.

        Subclasses may choose to override this method, calling
        ``Config.global_defaults`` and applying `.merge_dicts` to the result,
        to add to or modify these values.

        .. versionadded:: 1.0
        """
        ret: Dict[str, Any] = Config.global_defaults()
        extra_defaults = getattr(cls, "extra_defaults", None)
        if extra_defaults:
            debug(f"Using {cls} extra defaults: {extra_defaults}")
            ret = deep_merge(ret, cls.extra_defaults)

        ret["runners"]["local"] = NoStdoutRunner
        ret["run"]["echo_format"] = "[bold]{command}[/bold]"

        return ret


class _NotFound:  # pylint: disable=R0903
    """Sentinel object to distinguish 'not found' from None"""


_NOT_FOUND = _NotFound()


class _UndefinedDefault:  # pylint: disable=R0903
    """Sentinel object to distinguish "not defined" from None"""


_UNDEFINED_DEFAULT = _UndefinedDefault()


def _is_dict_like(obj: Any) -> bool:
    """Check if object supports dict-like operations"""
    return hasattr(obj, "__getitem__") and hasattr(obj, "__contains__")


def _navigate_config_path(config: "ToolkitConfig", path: str) -> tuple[Any, bool]:
    """
    Navigate through nested config using dot notation.

    Handles both regular dicts and DataProxy objects.

    Args:
        config: The ToolkitConfig object
        path: Dot-separated path (e.g., 'group.subgroup.key')

    Returns:
        Tuple of (value, found) where found is True if the path exists
    """
    keys = path.split(".")
    current = dict(config)

    for key in keys:
        if _is_dict_like(current) and key in current:
            current = current[key]
        else:
            return _NOT_FOUND, False

    return current, True


def _get_task_argument_name(path: str, depth: int = 3) -> Optional[str]:  # pylint: disable=too-many-return-statements
    """
    Try to infer the task argument name from the call stack.

    Walks up the call stack to find the invoke task and extracts
    the parameter name that corresponds to the config path.

    Attempts to match the first component of the path to a variable name.
    For example, if path is "api.key", looks for a variable named "api_key" or "api".

    Args:
        path: The config path being accessed (e.g., 'group.key')
        depth: How many frames to walk up

    Returns:
        The argument name if found, otherwise None
    """
    try:
        # Get the caller's frame
        frame = frame_inspect.currentframe()
        for _ in range(depth + 1):
            if frame is None:
                return None
            frame = frame.f_back

        if frame is None:
            return None

        # Extract the first component of the path
        path_components = path.split(".")
        first_component = path_components[0] if path_components else None

        if not first_component:
            return None

        # Get local variables from the task function
        local_vars = frame.f_locals

        # Skip common context variable names and private variables
        excluded = {"ctx", "context", "c", "self", "pyfuncitem"}

        # Try to find a variable that matches the path component
        for var_name in local_vars:
            if var_name in excluded or var_name.startswith("_"):
                continue

            # Exact match
            if var_name == first_component:
                return var_name

            # Snake case match (e.g., api_key for api)
            if var_name.startswith(first_component + "_"):
                return var_name

        # Fallback: return first non-excluded variable
        for var_name in local_vars:
            if var_name not in excluded and not var_name.startswith("_"):
                return var_name

        return None
    except Exception as error:  # pylint: disable=W0718
        debug(f"Getting {error} while looking for {path}")
        return None


# Overloads for type hints
# Returns T when no exit params
@overload
def get_config_value(
    ctx: "ToolkitContext",
    path: str,
    default: T = ...,
    exit_message: None = None,
    exit_code: None = None,
    required: bool = False,
) -> Any | T: ...


# Type hints NoReturn when exit_message provided
@overload
def get_config_value(
    ctx: "ToolkitContext",
    path: str,
    default: Any = _UNDEFINED_DEFAULT,
    exit_message: str = ...,
    exit_code: Optional[int] = None,
    required: bool = False,
) -> Any | NoReturn: ...


# Type hints NoReturn when exit_code provided
@overload
def get_config_value(
    ctx: "ToolkitContext",
    path: str,
    default: Any = _UNDEFINED_DEFAULT,
    exit_message: None = None,
    exit_code: int = ...,
    required: bool = False,
) -> Any | NoReturn: ...


# Type hints NoReturn when required=True
@overload
def get_config_value(
    ctx: "ToolkitContext",
    path: str,
    default: Any = _UNDEFINED_DEFAULT,
    exit_message: Optional[str] = None,
    exit_code: Optional[int] = None,
    required: bool = True,
) -> Any | NoReturn: ...


def get_config_value(  # pylint: disable=inconsistent-return-statements
    ctx: "ToolkitContext",
    path: str,
    default: Any = _UNDEFINED_DEFAULT,
    exit_message: Optional[str] = None,
    exit_code: Optional[int] = None,
    required: bool = False,
) -> Any:
    """
    Get a configuration value from the context config object with dot notation support.

    This helper function simplifies accessing nested configuration values using dot notation.
    It safely retrieves a value from the config, returning a default value if the path
    doesn't exist. Optionally supports automatic exit with rich formatting.

    Args:
        ctx: The ToolkitContext object from the task
        path: Dot-separated path to the config value (e.g., 'group.subgroup.key').
              Supports arbitrary nesting levels.
        default: The default value to return if the path is not found.
                  If not provided, returns None when value is not found and no exit params are set.
        exit_message: Custom message to display when value is required but missing.
                      If not provided and exit_code is set, will auto-detect the argument name.
        exit_code: Exit code to use when calling ctx.rich_exit(). If set, makes the value
                   required and triggers exit if not found.
        required: Whether the value is required. When True, automatically sets exit_code=1
                  and triggers exit if value is not found. Automatically set to True if exit_code
                  or exit_message is provided.

    Returns:
        The configuration value if found, otherwise the default value.
        If required, exit_message, or exit_code is provided and value is not found,
        calls ctx.rich_exit() and never returns (NoReturn).

    Raises:
        SystemExit: Raised via ctx.rich_exit() if required value is missing.

    Examples:
        >>> from invoke_toolkit import task, Context
        >>> from invoke_toolkit.config import get_config_value
        >>> @task()
        >>> def my_task(ctx: Context, db_host: str = "") -> None:
        >>>     # Simple usage
        >>>     db_host = db_host or get_config_value(
        >>>         ctx, "database.host", default="localhost"
        >>>     )
        >>>
        >>>     # With nested path and default
        >>>     db_port = get_config_value(
        >>>         ctx, "database.settings.port", default=5432
        >>>     )
        >>>
        >>>     # Required value with custom message
        >>>     api_key = get_config_value(
        >>>         ctx, "api.key",
        >>>         exit_code=2,
        >>>         exit_message="API key must be configured in 'api.key'"
        >>>     )
        >>>
        >>>     # Required value with auto-detected argument name
        >>>     secret = get_config_value(
        >>>         ctx, "secrets.token",
        >>>         exit_code=1  # Auto-detects 'secret' parameter name
        >>>     )
    """
    # Mark as required if exit parameters are provided or if required=True
    has_exit_params = (exit_message is not None) or (exit_code is not None) or required

    # Determine the exit code
    if exit_code is not None:
        final_exit_code = exit_code
    elif required:
        final_exit_code = 1
    else:
        final_exit_code = 1  # Default for exit_message-only case

    # Navigate through the nested config
    value, found = _navigate_config_path(ctx.config, path)

    # If found, return the value (even if it's falsy like False, 0, "", None)
    if found:
        return value

    # If not required and not found, return default
    if not has_exit_params:
        return None if default is _UNDEFINED_DEFAULT else default

    # Value is required but missing - prepare exit message
    if exit_message is None:
        # Try to infer the argument name from the call stack
        arg_name = _get_task_argument_name(path, depth=2)
        if arg_name:
            exit_message = (
                f"[red]Required configuration value not found:[/red] "
                f"[bold]{path}[/bold] (argument: [cyan]{arg_name}[/cyan])"
            )
        else:
            exit_message = (
                f"[red]Required configuration value not found:[/red] "
                f"[bold]{path}[/bold]"
            )

    # Exit with the message
    ctx.rich_exit(exit_message, exit_code=final_exit_code)
