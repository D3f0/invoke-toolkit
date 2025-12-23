"""
Class that implements the ctx.status through the config class
"""

from contextlib import contextmanager
from typing import Generator, Optional

from rich.console import Console, RenderableType
from rich.status import Status
from rich.style import StyleType

from invoke_toolkit.output import get_console


class NoOpStatus:
    """A no-op status object that prints messages on enter and exit"""

    def __init__(
        self,
        status: Optional[RenderableType] = None,
        console: Optional[Console] = None,
    ):
        self.status = status
        self.console = console or get_console()

    def __enter__(self) -> "NoOpStatus":
        """Print status message on enter"""
        if self.status:
            self.console.print(f"[bold blue]→[/bold blue] {self.status}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Print status message on exit"""
        if self.status:
            self.console.print(f"[bold green]✓[/bold green] {self.status}")

    def update(
        self,
        status: Optional[RenderableType] = None,
        *,
        spinner: Optional[str] = None,
        spinner_style: Optional[StyleType] = None,
        speed: Optional[float] = None,
    ) -> None:
        """No-op update"""

    def stop(self) -> None:
        """No-op stop"""


class StatusHelper:
    """
    A bridge to insert rich's status bound to a console into a invoke config, so
    it can be accessed from the task's context
    """

    _current_status: Optional[Status]
    _disabled: bool

    def __init__(self, console: Console, disabled: bool = False):
        self.console = console or get_console()
        self._current_status = None
        self._disabled = disabled

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
        if self._disabled:
            # When disabled, yield a no-op status object that prints messages
            with NoOpStatus(status=status, console=self.console) as noop:
                yield noop
            return

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
        if self._disabled:
            return

        if self._current_status:
            self._current_status.update(
                status, spinner=spinner, spinner_style=spinner_style, speed=speed
            )

    def status_stop(self) -> None:
        """Cancels the status. This will allow to use the REPL in debugging breakpoints"""
        if self._disabled:
            return

        if self._current_status:
            self._current_status.stop()
