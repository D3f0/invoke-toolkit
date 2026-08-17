"""
Invoke toolkit (internal) configuration tasks

This module demonstrates the proper use of completion callbacks through
invoke-toolkit's @task decorator system:

1. Callbacks are extracted from Annotated type hints via _extract_completion_callbacks
2. They are stored on the Task object as _completion_callbacks
3. The completion system retrieves them via get_choices_for_argument
4. This is clean, non-invasive, and follows the decorator pattern

The _complete_config_path callback is a good example of a reusable
completion function that can be:
- Applied to multiple parameters via Annotated types
- Used by other tasks that need config path completion
- Tested independently without touching invoke internals
"""

import ast
import json
from enum import Enum
from os.path import expanduser
from pathlib import Path
from typing import Annotated, Any

import yaml

from invoke_toolkit import Context, task

config = {"format": "yaml"}
SAFE_TYPES = (str, int, float, bool, type(None), list, dict, tuple)

# File suffixes supported by invoke
_FILE_SUFFIXES = ("yaml", "yml", "json", "py")


class ConfigLocation(str, Enum):
    """Config file location options"""

    LOCAL = "local"
    USER = "user"
    SYSTEM = "system"


def _clean_dict_for_serialization(data: Any) -> Any:
    """Remove non-serializable values from dictionary.

    Keeps: str, int, float, bool, None, list, dict
    Removes: class instances, functions, etc.
    """
    if isinstance(data, dict):
        return {
            k: _clean_dict_for_serialization(v)
            for k, v in data.items()
            if _is_serializable(v)
        }
    if isinstance(data, list):
        return [
            _clean_dict_for_serialization(item)
            for item in data
            if _is_serializable(item)
        ]
    return data


def _is_serializable(value):
    """Check if value is a primitive serializable type."""
    if value is None:
        return True
    if isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, (list, dict)):
        return True
    return False


def _get_config_prefix(ctx: Context) -> str:
    """Get the config file prefix from the context's config class.

    Returns the prefix used for config files (e.g., 'invoke' for invoke.yaml)
    """
    config_obj = ctx.config
    file_prefix = getattr(config_obj, "file_prefix", None)
    if file_prefix is not None:
        return file_prefix
    return getattr(config_obj, "prefix", "invoke")


def _get_config_file_paths(ctx: Context, location: ConfigLocation) -> list[Path]:
    """Get possible config file paths for a given location.

    Args:
        ctx: The context object
        location: Where to look for config files (local, user, system)

    Returns:
        List of possible config file paths (ordered by preference)
    """
    prefix = _get_config_prefix(ctx)
    paths: list[Path] = []

    if location == ConfigLocation.LOCAL:
        # Local config: ./invoke.{yaml,yml,json,py}
        for suffix in _FILE_SUFFIXES:
            paths.append(Path(f"./{prefix}.{suffix}"))
    elif location == ConfigLocation.USER:
        # User config: ~/.invoke.{yaml,yml,json,py}
        home = Path(expanduser("~"))
        for suffix in _FILE_SUFFIXES:
            paths.append(home / f".{prefix}.{suffix}")
    elif location == ConfigLocation.SYSTEM:
        # System config: /etc/invoke.{yaml,yml,json,py}
        for suffix in _FILE_SUFFIXES:
            paths.append(Path(f"/etc/{prefix}.{suffix}"))

    return paths


def _find_existing_config_file(ctx: Context, location: ConfigLocation) -> Path | None:
    """Find an existing config file at the given location.

    Returns the first config file that exists, or None if none found.
    """
    for path in _get_config_file_paths(ctx, location):
        if path.exists():
            return path
    return None


def _get_default_config_path(ctx: Context, location: ConfigLocation) -> Path:
    """Get the default config file path for a given location.

    Uses YAML format by default.
    """
    prefix = _get_config_prefix(ctx)

    if location == ConfigLocation.LOCAL:
        return Path(f"./{prefix}.yaml")
    if location == ConfigLocation.USER:
        return Path(expanduser(f"~/.{prefix}.yaml"))
    if location == ConfigLocation.SYSTEM:
        return Path(f"/etc/{prefix}.yaml")
    return Path(f"./{prefix}.yaml")


def _navigate_config_path(config_dict: dict, path: str) -> tuple[Any, bool]:
    """Navigate through nested config using dot notation.

    Args:
        config_dict: The config dictionary to navigate
        path: Dot-separated path (e.g., 'group.subgroup.key')

    Returns:
        Tuple of (value, found) where found is True if the path exists
    """
    keys = path.split(".")
    current = config_dict

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None, False

    return current, True


def _set_nested_value(config_dict: dict, path: str, value: Any) -> dict:
    """Set a value in a nested dictionary using dot notation.

    Args:
        config_dict: The config dictionary to modify
        path: Dot-separated path (e.g., 'group.subgroup.key')
        value: The value to set

    Returns:
        The modified config dictionary
    """
    keys = path.split(".")
    current = config_dict

    # Navigate to the parent of the target key, creating dicts as needed
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        elif not isinstance(current[key], dict):
            # Overwrite non-dict values with a dict
            current[key] = {}
        current = current[key]

    # Set the final key
    current[keys[-1]] = value
    return config_dict


def _remove_nested_value(config_dict: dict, path: str) -> dict:
    """Remove a value from a nested dictionary using dot notation.
    Args:
        config_dict: The config dictionary to modify
        path: Dot-separated path (e.g., 'group.subgroup.key')
    Returns:
        The modified config dictionary
    """
    keys = path.split(".")
    path_dicts = [config_dict]
    for key in keys[:-1]:
        last_dict = path_dicts[-1]
        if key in last_dict and isinstance(last_dict.get(key), dict):
            path_dicts.append(last_dict[key])
        else:
            # Path doesn't exist
            return config_dict

    # Remove the final key
    if keys[-1] in path_dicts[-1]:
        del path_dicts[-1][keys[-1]]

    # Clean up empty parent dictionaries
    for i in range(len(path_dicts) - 2, -1, -1):
        if not path_dicts[i + 1]:
            del path_dicts[i][keys[i]]
        else:
            break

    return config_dict


def _load_config_file(path: Path) -> dict:
    """Load a config file and return its contents as a dictionary.

    Supports yaml, yml, json, and py files.
    """
    if not path.exists():
        return {}

    suffix = path.suffix.lstrip(".")

    if suffix in ("yaml", "yml"):
        with open(path, encoding="utf-8") as fp:
            content = yaml.safe_load(fp)
            return content if content else {}
    elif suffix == "json":
        with open(path, encoding="utf-8") as fp:
            content = json.load(fp)
            return content if content else {}
    elif suffix == "py":
        # For Python config files, we need to execute them and get the resulting dict
        # Python config files typically just define a dict in module scope
        with open(path, encoding="utf-8") as fp:
            content = fp.read()
        # Execute the file and extract variables
        namespace: dict[str, Any] = {}
        exec(content, namespace)  # pylint: disable=exec-used
        # Filter out built-ins and return only user-defined values
        return {
            k: v
            for k, v in namespace.items()
            if not k.startswith("_") and _is_serializable(v)
        }

    return {}


def _save_config_file(path: Path, config_dict: dict) -> None:
    """Save a config dictionary to a file.

    The file format is determined by the file extension.
    Supports yaml, yml, json formats for writing.
    """
    suffix = path.suffix.lstrip(".")

    # Create parent directories if they don't exist
    path.parent.mkdir(parents=True, exist_ok=True)

    if suffix in ("yaml", "yml"):
        with open(path, "w", encoding="utf-8") as fp:
            yaml.safe_dump(config_dict, fp, default_flow_style=False)
    elif suffix == "json":
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(config_dict, fp, indent=2)
    elif suffix == "py":
        # For Python files, we write a simple assignment
        with open(path, "w", encoding="utf-8") as fp:
            for key, value in config_dict.items():
                fp.write(f"{key} = {repr(value)}\n")


def _parse_value(value_str: str) -> Any:
    """Parse a value string using ast.literal_eval.

    This allows setting complex values like lists and dicts from the CLI.

    Args:
        value_str: The string representation of the value

    Returns:
        The parsed value, or the original string if parsing fails
    """
    try:
        return ast.literal_eval(value_str)
    except (ValueError, SyntaxError):
        # If literal_eval fails, treat it as a plain string
        return value_str


# Basic types that we validate against
_BASIC_TYPES = (bool, int, float, str, list, dict, type(None))


def _get_expected_type(ctx: Context, path: str) -> type | None:
    """Get the expected type for a config path based on current config.

    Args:
        ctx: The context object
        path: Dot-separated config path

    Returns:
        The type of the existing value, or None if path doesn't exist
        or if the existing value is None (to allow setting any type)
    """
    config_dict = dict(ctx.config.items())
    value, found = _navigate_config_path(config_dict, path)

    if not found:
        return None

    # If the existing value is None, allow any type to be set
    if value is None:
        return None

    value_type = type(value)
    # Only return type if it's a basic type we want to validate
    if value_type in _BASIC_TYPES:
        return value_type

    return None


def _validate_type(
    value: Any, expected_type: type | None, path: str
) -> tuple[bool, str]:
    """Validate that a value matches the expected type.

    Args:
        value: The parsed value to validate
        expected_type: The expected type (or None to skip validation)
        path: The config path (for error messages)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if expected_type is None:
        # No existing value or unknown type, allow anything
        return True, ""

    actual_type = type(value)

    # Special case: allow int where float is expected (numeric promotion)
    if expected_type is float and actual_type is int:
        return True, ""

    # For dict and list, we don't check internal types
    if expected_type in (dict, list):
        if actual_type is expected_type:
            return True, ""
        return False, (
            f"Type mismatch for '{path}': expected {expected_type.__name__}, "
            f"got {actual_type.__name__}"
        )

    # For basic types, check exact match
    if actual_type is not expected_type:
        return False, (
            f"Type mismatch for '{path}': expected {expected_type.__name__}, "
            f"got {actual_type.__name__}"
        )

    return True, ""


def _get_all_config_paths(config_dict: dict, prefix: str = "") -> list[str]:
    """Recursively get all dot-notation paths from a config dictionary.

    Args:
        config_dict: The config dictionary to traverse
        prefix: Current path prefix for recursion

    Returns:
        List of all available dot-notation paths
    """
    paths: list[str] = []

    for key, value in config_dict.items():
        current_path = f"{prefix}.{key}" if prefix else key
        paths.append(current_path)

        # Recursively add nested paths
        if isinstance(value, dict):
            paths.extend(_get_all_config_paths(value, current_path))

    return paths


def _complete_config_path(ctx: Context, incomplete: str) -> list[str]:
    """Completion callback for config paths.

    Returns config paths that match the incomplete string.

    This callback demonstrates the proper way to create reusable completion
    callbacks using invoke-toolkit's @task decorator system. It's applied to
    task parameters via Annotated type hints:

        @task
        def my_task(ctx, path: Annotated[str, _complete_config_path]):
            pass

    The callback mechanism works as follows:
    1. The @task decorator extracts completion callbacks from Annotated types
    2. They are stored on the Task object as _completion_callbacks
    3. The completion system (in completion.py) retrieves them
    4. User types tab and shell displays completions

    This approach is clean, non-invasive, and doesn't require tapping into
    invoke internals. Callbacks have highest priority in the completion system
    (before enums, literals, and file markers).

    Completion callbacks support timeouts (default: 10 seconds):
    - Configure via environment: INVOKE_COMPLETION_CALLBACK_TIMEOUT=10.0
    - Or in invoke.yaml:
        completion:
          callback_timeout: 10.0

    Template for creating custom completion callbacks:

        def _complete_my_items(ctx: Context, incomplete: str) -> list[str]:
            '''Completion callback for my custom items.'''
            # Get data from config using context method (no import needed)
            items = ctx.get_config_value("my.items", default=[])

            # Filter by incomplete prefix
            matching = [i for i in items if i.startswith(incomplete)]

            return sorted(matching)

        @task
        def my_task(ctx, item: Annotated[str, _complete_my_items]):
            '''Task with auto-completion for items.'''

    Completion callbacks can be cached using the @cached decorator for persistent
    disk-based caching. This is essential for shell completion performance, as
    each completion request happens in a separate process.

        from invoke_toolkit import task, Context, cached
        from typing import Annotated

        @cached(ttl=300)  # Cache for 5 minutes
        def _complete_expensive_items(ctx: Context, incomplete: str) -> list[str]:
            '''Completion callback with persistent caching.'''
            # Expensive operation like API call or database query
            items = fetch_items_from_api()
            matching = [i for i in items if i.startswith(incomplete)]
            return sorted(matching)

        @task
        def deploy(ctx, target: Annotated[str, _complete_expensive_items]):
            '''Deploy to a target with cached completion.'''

    The @cached decorator uses diskcache for persistent storage, so results are
    cached across separate shell completion processes. Requires: pip install diskcache

    Callbacks are executed in a separate thread with a timeout (default: 10s).

    Note: Don't use functools.lru_cache for completion callbacks, as each shell
    completion happens in a separate process, making in-memory caching ineffective.
    Always use the @cached decorator for persistent disk-based caching:

        @cached(ttl=60)  # Short TTL for frequently changing data
        def _complete_active_deployments(ctx: Context, incomplete: str) -> list[str]:
            items = fetch_from_api()
            return [i for i in items if i.startswith(incomplete)]

        @cached(ttl=3600)  # Longer TTL for stable data
        def _complete_aws_regions(ctx: Context, incomplete: str) -> list[str]:
            return ["us-east-1", "us-west-2", "eu-west-1"]

    Args:
        ctx: The context object (contains config, run method, etc.)
        incomplete: The partial path typed by the user (for filtering)

    Returns:
        List of matching config paths sorted alphabetically
    """
    # Get current config as a clean dict
    config_dict = _clean_dict_for_serialization(dict(ctx.config.items()))

    # Get all available paths
    all_paths = _get_all_config_paths(config_dict)

    # Filter paths that start with the incomplete string
    if incomplete:
        matching = [p for p in all_paths if p.startswith(incomplete)]
    else:
        matching = all_paths

    return sorted(matching)


@task(
    default=True,
    autoprint=True,
    help={
        "serializable": "Controls if non-editable/composed configuration are shown/exported",
        "configs": "Select configuration sections to show",
    },
)
def show(
    ctx: Context,
    configs: list[str] = [],
    serializable: bool = True,
    format_: str = "python",
):
    """
    Shows the contents of the configuration in the context
    """
    ctx.print_err(f"{serializable=}")
    if ctx.config.run.echo:
        ctx.print(f"Showing sections: {configs}")
    # All sections or the selected ones
    items = {k: v for k, v in ctx.config.items() if not configs or k in configs}

    # Now ensure the values are serializable
    if serializable:
        items = _clean_dict_for_serialization(items)

    format_ = format_.lower()
    if format_ in {"y", "yaml"}:
        return yaml.safe_dump(
            items,
        )
    if format_ in {"j", "json"}:
        return json.dumps(items)
    return items


@task(
    autoprint=True,
    help={
        "path": "Dot-separated path to the config value (e.g., 'run.echo', 'tasks.auto_dash_names')",
        "format_": "Output format: 'raw' (default), 'json', 'yaml', or 'python'",
    },
)
def get(
    ctx: Context,
    path: Annotated[str, _complete_config_path],
    format_: str = "raw",
):
    """
    Get a configuration value using dot notation.

    Examples:
        invoke-toolkit -x config.get run.echo
        invoke-toolkit -x config.get tasks.auto_dash_names
        invoke-toolkit -x config.get run --format yaml
    """
    # Convert config to a clean dict for navigation
    # Use items() because Config is a special proxy class that doesn't work with dict()
    config_dict = _clean_dict_for_serialization(dict(ctx.config.items()))

    value, found = _navigate_config_path(config_dict, path)

    if not found:
        ctx.print_err(f"[yellow]Config path not found:[/yellow] [bold]{path}[/bold]")
        return None

    format_ = format_.lower()
    if format_ == "raw":
        return value
    if format_ in {"j", "json"}:
        return json.dumps(value, indent=2)
    if format_ in {"y", "yaml"}:
        return yaml.safe_dump(value, default_flow_style=False)
    if format_ in {"p", "python"}:
        return repr(value)

    return value


@task(
    name="set",
    help={
        "path": "Dot-separated path to set (e.g., 'run.echo', 'custom.api_key')",
        "value": "Value to set (supports literals via ast.literal_eval: lists, dicts, etc.)",
        "location": "Where to save: 'local' (default), 'user', or 'system'",
        "format_": "File format to use if creating new file: 'yaml' (default), 'json'",
        "no_validate": "Skip schema validation",
    },
)
def set_(
    ctx: Context,
    path: Annotated[str | None, _complete_config_path] = None,
    value: str | None = None,
    location: ConfigLocation = ConfigLocation.LOCAL,
    format_: str = "yaml",
    no_validate: bool = False,
):
    """
    Set a configuration value in a config file.

    The value is parsed using ast.literal_eval, allowing you to set:
    - Strings: 'hello' or just hello
    - Numbers: 42, 3.14
    - Booleans: True, False
    - Lists: [1, 2, 3] or ['a', 'b']
    - Dicts: {'key': 'value'}

    If a schema is registered for the config path's collection, the value
    will be validated against the expected type. Use --no-validate to skip.

    Examples:
        invoke-toolkit -x config.set run.echo True
        invoke-toolkit -x config.set custom.ports "[8080, 8443]"
        invoke-toolkit -x config.set custom.settings "{'debug': True}"
        invoke-toolkit -x config.set api.key "my-secret-key" --location user
    """
    from invoke_toolkit.config.registry import get_field_type, validate_value

    # Validate required arguments
    if path is None or value is None:
        ctx.print_err(
            "[red]Error:[/red] Both 'path' and 'value' are required.\n"
            "[dim]Usage: config.set <path> <value>[/dim]\n"
            "[dim]Use --help for more information.[/dim]"
        )
        return

    # Parse the value
    parsed_value = _parse_value(value)

    # Validate against schema (if registered and not disabled)
    if not no_validate:
        is_valid, schema_error = validate_value(path, parsed_value)
        if not is_valid:
            ctx.print_err(f"[red]Validation error:[/red] {schema_error}")
            ctx.print_err(f"[dim]Path: {path}[/dim]")
            ctx.print_err(f"[dim]Value: {parsed_value!r}[/dim]")

            # Show expected type hint
            expected = get_field_type(path)
            if expected:
                type_name = getattr(expected, "__name__", str(expected))
                ctx.print_err(f"[dim]Expected type: {type_name}[/dim]")

            raise SystemExit(1)

    # Validate type against existing config value (legacy behavior)
    expected_type = _get_expected_type(ctx, path)
    is_valid, error_msg = _validate_type(parsed_value, expected_type, path)

    if not is_valid:
        ctx.print_err(f"[red]Error:[/red] {error_msg}")
        ctx.print_err(
            f"[dim]Hint: Use the correct type or check the existing value with "
            f"'config.get {path}'[/dim]"
        )
        return

    # Find existing config file or determine default path
    config_path = _find_existing_config_file(ctx, location)

    if config_path is None:
        # No existing config file, create one with the specified format
        prefix = _get_config_prefix(ctx)
        format_suffix = format_.lower()
        if format_suffix in ("yaml", "yml"):
            format_suffix = "yaml"
        elif format_suffix != "json":
            format_suffix = "yaml"  # Default to yaml

        if location == ConfigLocation.LOCAL:
            config_path = Path(f"./{prefix}.{format_suffix}")
        elif location == ConfigLocation.USER:
            config_path = Path(expanduser(f"~/.{prefix}.{format_suffix}"))
        elif location == ConfigLocation.SYSTEM:
            config_path = Path(f"/etc/{prefix}.{format_suffix}")

    # At this point config_path is guaranteed to be set
    assert config_path is not None

    # Check if we can write to a .py file
    if config_path.suffix == ".py":
        ctx.print_err(
            "[yellow]Warning:[/yellow] Python config files (.py) have limited write support. "
            "Consider using YAML or JSON format."
        )

    # Load existing config
    config_dict = _load_config_file(config_path)

    # Set the new value
    config_dict = _set_nested_value(config_dict, path, parsed_value)

    # Save the config
    _save_config_file(config_path, config_dict)

    ctx.print(f"[green]✓[/green] Set [bold]{path}[/bold] = {repr(parsed_value)}")
    ctx.print(f"  [dim]Saved to: {config_path}[/dim]")


@task(
    name="unset",
    help={
        "path": "Dot-separated path to unset (e.g., 'run.echo', 'custom.api_key')",
        "location": "Where to save: 'local' (default), 'user', or 'system'",
    },
)
def unset(
    ctx: Context,
    path: Annotated[str | None, _complete_config_path] = None,
    location: ConfigLocation = ConfigLocation.LOCAL,
):
    """
    Unset a configuration value in a config file.

    Examples:
        invoke-toolkit -x config.unset run.echo
        invoke-toolkit -x config.unset custom.ports
    """
    if path is None:
        ctx.print_err(
            "[red]Error:[/red] 'path' is required.\n"
            "[dim]Usage: config.unset <path>[/dim]\n"
            "[dim]Use --help for more information.[/dim]"
        )
        return

    config_path = _find_existing_config_file(ctx, location)
    if not config_path or not config_path.exists():
        ctx.print_err(
            f"[yellow]No config file found at location '{location}'. Nothing to do.[/yellow]"
        )
        return

    config_dict = _load_config_file(config_path)
    original_config = config_dict.copy()
    config_dict = _remove_nested_value(config_dict, path)

    if config_dict == original_config:
        ctx.print_err(
            f"[yellow]Path '[bold]{path}[/bold]' not found in the configuration. Nothing to do.[/yellow]"
        )
        return

    _save_config_file(config_path, config_dict)
    ctx.print(f"[green]✓[/green] Unset [bold]{path}[/bold]")
    ctx.print(f"  [dim]Saved to: {config_path}[/dim]")


def _print_nested_schema(
    ctx: Context, prefix: str, data: dict, indent: int = 2
) -> None:
    """Print nested schema fields recursively."""
    for key, value in data.items():
        path = f"{prefix}.{key}"
        spaces = " " * indent

        if isinstance(value, dict):
            ctx.print(f"{spaces}[green]{path}[/green]: [dim]{{...}}[/dim]")
            _print_nested_schema(ctx, path, value, indent + 2)
        elif isinstance(value, str):
            ctx.print(f'{spaces}[green]{path}[/green] = [yellow]"{value}"[/yellow]')
        else:
            ctx.print(f"{spaces}[green]{path}[/green] = [yellow]{value}[/yellow]")


@task(
    name="schemas",
    help={
        "collection": "Filter to a specific collection",
        "verbose": "Show full descriptions and nested schema details",
    },
)
def schemas(  # pylint: disable=too-many-branches
    ctx: Context, collection: str | None = None, verbose: bool = False
) -> None:
    """Show available config schemas.

    Lists all registered config schemas with their fields and default values.

    Args:
        collection: Filter to a specific collection
        verbose: Show full descriptions and nested schema details

    Example:
        intk -x config.schemas
        intk -x config.schemas --collection weather
        intk -x config.schemas --verbose
    """
    from invoke_toolkit.config.registry import (
        get_all_schemas,
        get_schema,
        get_schema_info,
    )

    if collection:
        schema = get_schema(collection)
        if schema is None:
            ctx.print_err(
                f"[red]No schema registered for collection: {collection}[/red]"
            )
            raise SystemExit(1)
        schemas_to_show = {collection: schema}
    else:
        schemas_to_show = get_all_schemas()

    if not schemas_to_show:
        ctx.print("[yellow]No config schemas registered.[/yellow]")
        ctx.print(
            "[dim]Schemas are registered when extensions with @config_schema are loaded.[/dim]"
        )
        return

    for coll_name, schema_cls in sorted(schemas_to_show.items()):
        info = get_schema_info(schema_cls)

        # Header
        ctx.print(
            f"\n[bold cyan]{coll_name}[/bold cyan] [dim]({info['class_name']})[/dim]"
        )

        # Description
        if info.get("description") and verbose:
            desc = info["description"].strip().split("\n")[0]  # First line
            ctx.print(f"  [dim]{desc}[/dim]")

        # Fields
        if info.get("fields"):
            ctx.print()
            for field in info["fields"]:
                name = field["name"]
                type_str = field["type"]
                default = field["default"]
                required = field["required"]

                # Format the line
                if required:
                    marker = "[red]*[/red]"
                else:
                    marker = " "

                # Format default value
                if isinstance(default, dict):
                    # Nested schema
                    default_str = "[dim]{...}[/dim]"
                    if verbose:
                        ctx.print(
                            f"  {marker} [green]{coll_name}.{name}[/green]: "
                            f"[blue]{type_str}[/blue]"
                        )
                        _print_nested_schema(
                            ctx, f"{coll_name}.{name}", default, indent=4
                        )
                        continue
                elif default is None and not required:
                    default_str = "[dim]None[/dim]"
                elif isinstance(default, str):
                    default_str = f'[yellow]"{default}"[/yellow]'
                else:
                    default_str = f"[yellow]{default}[/yellow]"

                ctx.print(
                    f"  {marker} [green]{coll_name}.{name}[/green]: "
                    f"[blue]{type_str}[/blue] = {default_str}"
                )

        ctx.print()

    # Legend
    ctx.print("[dim]Legend: [red]*[/red] = required field[/dim]")
    ctx.print("[dim]Use --verbose for full details[/dim]")
