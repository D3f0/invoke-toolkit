"""Package namespace imports"""

# pyright: reportPrivateUsage=false, reportUnusedImport=false, reportMissingTypeStubs=false, reportPrivateImportUsage=false, reportAny=false

import sys
from importlib import metadata
from typing import Any

# Keep this import in the top
from invoke_toolkit.collections import ToolkitCollection as Collection  # noqa
from invoke_toolkit.config.config import ToolkitConfig as Config  # noqa
from invoke_toolkit.context import ToolkitContext as Context  # noqa
from invoke_toolkit.scripts.loader import script  # noqa
from invoke_toolkit.tasks import call, task  # noqa

# Ugly hack to prevent auto-sorting of imports preventing the logging setup
_KEEP_IMPORTS_SORTED = None

from invoke.context import MockContext  # noqa
from invoke.exceptions import (  # noqa
    AmbiguousEnvVar,
    AuthFailure,
    CollectionNotFound,
    CommandTimedOut,
    Exit,
    ParseError,
    PlatformError,
    ResponseNotAccepted,
    SubprocessPipeError,
    ThreadException,
    UncastableEnvVar,
    UnexpectedExit,
    UnknownFileType,
    UnpicklableConfigMember,
    WatcherError,
)
from invoke.executor import Executor  # noqa
from invoke.loader import FilesystemLoader  # noqa
from invoke.parser import Argument, Parser, ParserContext, ParseResult  # noqa
from invoke.program import Program  # noqa
from invoke.runners import Failure, Local, Promise, Result, Runner  # noqa

from invoke.tasks import Call, Task  # noqa
from invoke.terminals import pty_size  # noqa
from invoke.watchers import FailingResponder, Responder, StreamWatcher  # noqa

__version__ = metadata.version("invoke_toolkit")


# __all__ = ["task", "Context", "run", "script"]


def _config() -> "Config":
    """Creates a configuration suitable for top-level usage"""
    if hasattr(sys.stdin, "isatty") and not sys.stdin.isatty():
        overrides = {"run": {"in_stream": False}}
    else:
        overrides = {}
    config = Config(overrides=overrides)
    return config


def run(command: str, **kwargs: Any) -> "Result| None":
    """
    Run `command` in a subprocess and return a `.Result` object.

    See `.Runner.run` for API details.


    > This function is a convenience wrapper around Invoke's `.Context` and
    > `.Runner` APIs.

    > Specifically, it creates an anonymous `.Context` instance and calls its
    > `~.Context.run` method, which in turn defaults to using a `.Local`
    > runner subclass for command execution.
    """
    return Context(config=_config()).run(command, **kwargs)


def sudo(command: str, **kwargs: Any) -> Result | None:
    """
    Run ``command`` in a ``sudo`` subprocess and return a `.Result` object.

    See `.Context.sudo` for API details, such as the ``password`` kwarg.

    .. note::
        This function is a convenience wrapper around Invoke's `.Context` and
        `.Runner` APIs.

        Specifically, it creates an anonymous `.Context` instance and calls its
        `~.Context.sudo` method, which in turn defaults to using a `.Local`
        runner subclass for command execution (plus sudo-related bits &
        pieces).

    .. versionadded:: 1.4
    """
    return Context().sudo(command, **kwargs)
