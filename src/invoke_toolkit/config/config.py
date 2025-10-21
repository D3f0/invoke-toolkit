"""
Custom config class passed in every context class as .config
This module defines some functions/callables
"""

from typing import Any, Dict

from invoke.config import Config


from ..runners.rich import NoStdoutRunner


class InvokeToolkitConfig(Config):
    """
    Config object used for resolving ctx attributes and functions
    such as .cd, .run, etc.
    """

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
