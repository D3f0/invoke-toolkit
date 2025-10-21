"""
Invoke toolkit (internal) configuration tasks
"""

import json

import yaml

from invoke_toolkit import Context, task

config = {"format": "yaml"}
SAFE_TYPES = (str, int, float, bool, type(None), list, dict, tuple)


def _clean_dict_for_serialization(data):
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
