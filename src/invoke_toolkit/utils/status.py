from rich.status import Status, RenderableType, StyleType
from rich.console import Console
from typing import Optional
from invoke.util import debug


class SatusHelper:
    """
    This class should concentrate the status updates in the context
    through the config getattr proxy
    """

    console: Console
    _current_status: Status | None = None

    def __init__(self, console: Console) -> None:
        self.console = console

    def status(
        self,
        status: RenderableType,
        *,
        console: Optional[Console] = None,
        spinner: str = "dots",
        spinner_style: StyleType = "status.spinner",
        speed: float = 1.0,
        refresh_per_second: float = 12.5,
    ):
        if self._current_status:
            debug("There's an active status in the context")
            self.update(st)
        with self.console.status(
            status=status,
            spinner=spinner,
            spinner_style=spinner_style,
            speed=speed,
            refresh_per_second=refresh_per_second,
        ) as status:
            self._current_status = status

    def update(
        self,
        status: Optional[RenderableType] = None,
        *,
        spinner: Optional[str] = None,
        spinner_style: Optional[StyleType] = None,
        speed: Optional[float] = None,
    ):
        if self._current_status:
            self._current_status.update(
                status=status,
                spinner=spinner,
                speed=speed,
            )
        else:
            self.status(
                status=status,
                spinner=spinner,
                spinner_style=spinner_style,
                speed=speed,
            )

    def cancel(self):
        if self._current_status:
            self._current_status.cancel()
        else:
            debug("No status active in current context")
