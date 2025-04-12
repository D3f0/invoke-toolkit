"""
Extend the config object used by invoke inside the context
passed as the first argument to every task.

The context object is has a dedicated attribute access method
that will look up for methods/attributes in the config object
after not resolving them inside of the Context class.

NOTE: The context class is created in the tasks.Call class which
is not particularly extendable in the Program class.
"""

from invoke.config import Config, Local
from invoke.terminals import WINDOWS
from typing import Dict, Any
from .runner import InvokeToolkitRunner
from invoke_toolkit.output import rich_exit


from copy import copy

GLOBAL_DEFAULTS = {
    "run": {
        "asynchronous": False,
        "disown": False,
        "dry": False,
        "echo": False,
        "echo_stdin": None,
        "encoding": None,
        "env": {},
        "err_stream": None,
        "fallback": True,
        "hide": None,
        "in_stream": None,
        "out_stream": None,
        "echo_format": "\033[1;37m{command}\033[0m",
        "pty": False,
        "replace_env": False,
        # "shell": shell,
        "warn": False,
        "watchers": [],
    },
    # This doesn't live inside the 'run' tree; otherwise it'd make it
    # somewhat harder to extend/override in Fabric 2 which has a split
    # local/remote runner situation.
    # "runners": {"local": Local},
    "sudo": {
        "password": None,
        "prompt": "[sudo] password: ",
        "user": None,
    },
    "tasks": {
        "auto_dash_names": True,
        "collection_name": "tasks",
        "dedupe": True,
        "executor_class": None,
        "ignore_unknown_help": False,
        "search_root": None,
    },
    "timeouts": {"command": None},
}

# TODO: Implement the protocol for autocompletion in tasks


class InvokeToolkitConfig(Config):
    @staticmethod
    def global_defaults() -> Dict[str, Any]:
        """
        Return the core default settings for Invoke Toolkit.

        Look at the definition of the supper class
        """

        # global_defaults = Config.global_defaults()

        if WINDOWS:
            shell = os.environ.get("COMSPEC", "cmd.exe")
        # Else, assume Unix, most distros of which have /bin/bash available.
        # TODO: consider an automatic fallback to /bin/sh for systems lacking
        # /bin/bash; however users may configure run.shell quite easily, so...
        else:
            shell = "/bin/bash"

        global_defaults = copy(GLOBAL_DEFAULTS)
        global_defaults.update(
            runners={"local": Local},
        )
        global_defaults["run"]["shell"] = shell
        # Change the default runner
        global_defaults["runners"]["local"] = InvokeToolkitRunner
        # Callable attributes

        callables = {
            "rich_exit": rich_exit,
        }

        return global_defaults | callables
