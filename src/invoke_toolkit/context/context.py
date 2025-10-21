"""Context object for invoke_toolkit tasks"""

import sys
from invoke.context import Context
from typing import (
    Callable,
    Generator,
    NoReturn,
    Optional,
    Protocol,
    TYPE_CHECKING,
)
from invoke_toolkit.config import InvokeToolkitConfig
from invoke_toolkit.config.status_helper import StatusHelper
from invoke_toolkit.output.console import get_console
from .types import BoundPrintProtocol, ContextRunProtocol


from rich import inspect

if TYPE_CHECKING:
    from rich.console import Console
    from rich.status import Status
    # from rich.console import RenderableType, StyleType


class ConfigProtocol(Protocol):
    """Type annotated override"""

    status: Generator["Status", None, None]
    console: "Console"
    status_stop: Callable
    status_update: Callable
    # rich_exit: Callable[[str, Optional[int]], NoReturn]
    rich_exit: Callable[[str, int], NoReturn]
    print: BoundPrintProtocol


class InvokeToolkitContext(Context, ConfigProtocol):
    """Type annotated override"""

    run: ContextRunProtocol
    _console: "Console"
    _config: InvokeToolkitConfig
    _status_helper: StatusHelper

    def __init__(self, config: Optional[InvokeToolkitConfig] = None) -> None:
        super().__init__(config)
        self._set("_console", get_console())
        self._set("_status_helper", StatusHelper(console=self._console))

    @property
    def console(self) -> "Console":
        """A console instance to do rich output"""
        console = get_console()
        return console

    # @contextmanager
    @property
    def status(self):
        """A rich Context manager to show progress on long running tasks"""
        return self._status_helper.status

    @property
    def status_update(
        self,
    ):
        """Updates the status."""
        return self._status_helper.status_update

    def status_stop(self) -> None:
        """
        Clears all status
        Helpful when debugging
        """
        return self._status_helper.status_stop()

    def rich_exit(self, message: str = "Exited", exit_code=1) -> NoReturn:
        """An alternative to sys.exit that has rich output"""
        get_console().log(message)
        sys.exit(exit_code)

    @property
    def print(self):
        """Rich print, use square bracketed markup for color/highlights"""
        return get_console("out").print

    @property
    def print_err(self):
        """Rich print, use square bracketed markup for color/highlights"""
        return self._console.print

    def inspect(
        self,
        obj,
        *,
        # console: Optional["Console"] = None,
        title: Optional[str] = None,
        help_: bool = False,
        methods: bool = False,
        docs: bool = True,
        private: bool = False,
        dunder: bool = False,
        sort: bool = True,
        all_: bool = False,
        value: bool = True,
    ):
        """Runs inspect on an object"""
        return inspect(
            obj,
            console=self._console,
            title=title,
            help=help_,
            methods=methods,
            docs=docs,
            private=private,
            dunder=dunder,
            sort=sort,
            all=all_,
            value=value,
        )
