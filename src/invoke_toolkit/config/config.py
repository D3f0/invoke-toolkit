"""
Custom config class passed in every context class as .config
This module defines some functions/callables
"""

from typing import Any, Dict, Optional

from invoke.config import Config
from invoke.util import debug

from ..runners.rich import NoStdoutRunner


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
