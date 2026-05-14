"""
Class that implements the ctx.status through the config class
"""

from collections import deque
from contextlib import contextmanager
from typing import Generator, Optional, Union

from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.status import Status
from rich.style import StyleType
from rich.text import Text

from invoke_toolkit.output import get_console

MAX_OUTPUT_LINES = 3


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

    def capture_line(self, line: str) -> None:
        """No-op capture"""


class VerboseStatus:  # pylint: disable=too-many-instance-attributes
    """Status that shows the last N lines of command output below the spinner."""

    def __init__(
        self,
        status: RenderableType,
        *,
        console: Optional[Console] = None,
        spinner: str = "dots",
        spinner_style: StyleType = "status.spinner",
        speed: float = 1.0,
        refresh_per_second: float = 12.5,
        max_lines: int = MAX_OUTPUT_LINES,
    ):
        self.status = status
        self.spinner_style = spinner_style
        self.speed = speed
        self._lines: deque[str] = deque(maxlen=max_lines)
        self._spinner = Spinner(spinner, text=status, style=spinner_style, speed=speed)
        self._console = console or get_console()
        self._live = Live(
            self._build_renderable(),
            console=self._console,
            refresh_per_second=refresh_per_second,
            transient=True,
        )

    def _build_renderable(self) -> RenderableType:
        """Build the composite renderable: spinner + output panel."""
        if not self._lines:
            return self._spinner
        output_text = Text("\n".join(self._lines), style="dim")
        panel = Panel(
            output_text,
            border_style="dim",
            padding=(0, 1),
            expand=True,
        )
        return Group(self._spinner, panel)

    def capture_line(self, line: str) -> None:
        """Append a line of output and refresh the live display."""
        self._lines.append(line.rstrip("\n\r"))
        self._live.update(self._build_renderable())

    def update(
        self,
        status: Optional[RenderableType] = None,
        *,
        spinner: Optional[str] = None,
        spinner_style: Optional[StyleType] = None,
        speed: Optional[float] = None,
    ) -> None:
        """Update the status text or spinner parameters."""
        if status is not None:
            self.status = status
        if spinner_style is not None:
            self.spinner_style = spinner_style
        if speed is not None:
            self.speed = speed
        if spinner is not None:
            self._spinner = Spinner(
                spinner, text=self.status, style=self.spinner_style, speed=self.speed
            )
        else:
            self._spinner.update(
                text=self.status, style=self.spinner_style, speed=self.speed
            )
        self._live.update(self._build_renderable())

    def start(self) -> None:
        """Start the live display."""
        self._live.start()

    def stop(self) -> None:
        """Stop the live display."""
        self._live.stop()

    def __enter__(self) -> "VerboseStatus":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()


class StatusHelper:
    """
    A bridge to insert rich's status bound to a console into a invoke config, so
    it can be accessed from the task's context
    """

    _current_status: Optional[Union[Status, VerboseStatus]]
    _disabled: bool
    _show_command_output: bool

    def __init__(
        self,
        console: Console,
        disabled: bool = False,
        show_command_output: bool = False,
    ):
        self.console = console or get_console()
        self._current_status = None
        self._disabled = disabled
        self._show_command_output = show_command_output

    @contextmanager
    def status(
        self,
        status: RenderableType,
        *,
        spinner: str = "dots",
        spinner_style: StyleType = "status.spinner",
        speed: float = 1.0,
        refresh_per_second: float = 12.5,
    ) -> Generator[Union[Status, VerboseStatus], None, None]:
        """Context manager for status management"""
        if self._disabled:
            with NoOpStatus(status=status, console=self.console) as noop:
                yield noop  # type: ignore[misc]
            return

        if self._current_status is not None:
            # Nested status: update the existing one
            self._current_status.update(
                status, spinner=spinner, spinner_style=spinner_style, speed=speed
            )
            yield self._current_status
        elif self._show_command_output:
            verbose = VerboseStatus(
                status=status,
                console=self.console,
                spinner=spinner,
                spinner_style=spinner_style,
                speed=speed,
                refresh_per_second=refresh_per_second,
            )
            with verbose as self._current_status:  # type: ignore[assignment]
                yield self._current_status
            self._current_status = None
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

    def capture_line(self, line: str) -> None:
        """Feed a line of output to the current verbose status display."""
        if isinstance(self._current_status, VerboseStatus):
            self._current_status.capture_line(line)

    @property
    def is_verbose(self) -> bool:
        """Whether the current status is a VerboseStatus."""
        return isinstance(self._current_status, VerboseStatus)

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
