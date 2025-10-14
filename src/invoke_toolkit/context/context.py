"""Context object for invoke_toolkit tasks"""

from invoke.context import Context
from typing import (
    Callable,
    Generator,
    NoReturn,
    Protocol,
    TYPE_CHECKING,
)
from invoke_toolkit.config import InvokeToolkitConfig
from .types import BoundPrintProtocol

if TYPE_CHECKING:
    from rich.console import Console
    from rich.status import Status


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

    _config: InvokeToolkitConfig
