"""
Invoke toolkit (internal) configuration tasks
"""

import ast
import json
from enum import Enum
from os.path import expanduser
from pathlib import Path
from typing import Annotated, Any, Optional

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


def _find_existing_config_file(
    ctx: Context, location: ConfigLocation
) -> Optional[Path]:
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

    Args:
        ctx: The context object
        incomplete: The partial path typed by the user

    Returns:
        List of matching config paths
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
    },
)
def set_(
    ctx: Context,
    path: Annotated[str, _complete_config_path],
    value: str,
    location: ConfigLocation = ConfigLocation.LOCAL,
    format_: str = "yaml",
):
    """
    Set a configuration value in a config file.

    The value is parsed using ast.literal_eval, allowing you to set:
    - Strings: 'hello' or just hello
    - Numbers: 42, 3.14
    - Booleans: True, False
    - Lists: [1, 2, 3] or ['a', 'b']
    - Dicts: {'key': 'value'}

    Examples:
        invoke-toolkit -x config.set run.echo True
        invoke-toolkit -x config.set custom.ports "[8080, 8443]"
        invoke-toolkit -x config.set custom.settings "{'debug': True}"
        invoke-toolkit -x config.set api.key "my-secret-key" --location user
    """
    # Parse the value
    parsed_value = _parse_value(value)

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
