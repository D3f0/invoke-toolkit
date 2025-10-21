"""
Custom config class passed in every context class as .config
This module defines some functions/callables
"""

from typing import Any, Dict

from invoke.config import Config


from ..runners.rich import NoStdoutRunner


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
        cls, prefix=None, file_prefix=None, env_prefix=None, **kwargs
    ):
        super().__init_subclass__(**kwargs)
        if prefix is not None:
            cls.prefix = prefix
        if file_prefix is not None:
            cls.file_prefix = file_prefix
        if env_prefix is not None:
            cls.env_prefix = env_prefix

    @staticmethod
    def global_defaults() -> Dict[str, Any]:
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
        ret["runners"]["local"] = NoStdoutRunner
        ret["run"]["echo_format"] = "[bold]{command}[/bold]"
        return ret
