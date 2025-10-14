"""
Class that implements the ctx.status through the config class
"""

from contextlib import contextmanager
from typing import Generator, Optional

from rich.console import Console, RenderableType
from rich.style import StyleType
from rich.status import Status

from invoke_toolkit.output import get_console


class StatusHelper:
    """
    A bridge to insert rich's status bound to a console into a invoke config, so
    it can be accessed from the task's context
    """

    _current_status: Optional[Status]

    def __init__(self, console: Console):
        self.console = console or get_console()
        self._current_status = None

    @contextmanager
    def status(
        self,
        status: RenderableType,
        *,
        spinner: str = "dots",
        spinner_style: StyleType = "status.spinner",
        speed: float = 1.0,
        refresh_per_second: float = 12.5,
    ) -> Generator[Status, None, None]:
        """Context manager for status management"""
        if self._current_status is not None:
            self._current_status.update(
                status, spinner=spinner, spinner_style=spinner_style, speed=speed
            )
            yield self._current_status
        else:
            with self.console.status(
                status=status,
                spinner=spinner,
                spinner_style=spinner_style,
                speed=speed,
                refresh_per_second=refresh_per_second,
            ) as self._current_status:
                yield self._current_status
            self._current_status = None

    def status_update(
        self,
        status: Optional[RenderableType] = None,
        *,
        spinner: Optional[str] = None,
        spinner_style: Optional[StyleType] = None,
        speed: Optional[float] = None,
    ) -> None:
        """Wrapper on Status.update"""
        if self._current_status:
            self._current_status.update(
                status, spinner=spinner, spinner_style=spinner_style, speed=speed
            )

    def status_stop(self) -> None:
        """Cancels the status. This will allow to use the REPL in debugging breakpoints"""
        if self._current_status:
            self._current_status.stop()
