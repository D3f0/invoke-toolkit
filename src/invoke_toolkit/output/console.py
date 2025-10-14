"""
Rich console instance
"""

from rich.console import Console

_console: Console | None = None


def get_console() -> "Console":
    """Returns the console"""
    global _console  # pylint: disable=global-statement
    if _console is None:
        _console = Console(stderr=True)
    return _console
