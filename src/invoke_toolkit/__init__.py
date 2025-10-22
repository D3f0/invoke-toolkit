"""Package namespace imports"""

from typing import Any, Optional, TYPE_CHECKING
from invoke_toolkit.tasks import task
from invoke_toolkit.context import ToolkitContext as Context
from invoke_toolkit.scripts.loader import script

if TYPE_CHECKING:
    from invoke.runners import Result


__all__ = ["task", "Context", "run", "script"]


def run(command: str, **kwargs: Any) -> Optional["Result"]:
    """
    Run `command` in a subprocess and return a `.Result` object.

    See `.Runner.run` for API details.


    > This function is a convenience wrapper around Invoke's `.Context` and
    > `.Runner` APIs.

    > Specifically, it creates an anonymous `.Context` instance and calls its
    > `~.Context.run` method, which in turn defaults to using a `.Local`
    > runner subclass for command execution.
    """
    return Context().run(command, **kwargs)
