"""
Custom config class passed in every context class as .config
This module defines some functions/callables
"""

from typing import Any, Dict, Optional

from invoke.config import Config
from rich import inspect
from rich.status import Status

from invoke_toolkit.output import get_console, rich_exit

from ..runners.rich import NoStdoutRunner
from .status_helper import StatusHelper


class InvokeToolkitConfig(Config):
    """
    Config object used for resolving ctx attributes and functions
    such as .cd, .run, etc.
    """

    _current_status: Optional[Status]

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
        console = get_console()

        status_helper = StatusHelper(console=console)

        ret.update(
            {
                "console": console,
                "status": status_helper.status,
                "status_stop": status_helper.status_stop,
                "status_update": status_helper.status_update,
                "rich_exit": rich_exit,
                "print": console.print,
                "inspect": inspect,
            }
        )
        ret["runners"]["local"] = NoStdoutRunner
        ret["run"]["echo_format"] = "[bold]{command}[/bold]"
        return ret
