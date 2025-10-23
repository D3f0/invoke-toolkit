"""
Logging setup using rich
"""

import logging

from rich.logging import RichHandler
from rich.traceback import install as install_traceback_handler

from invoke_toolkit.output import get_console


def setup_rich_logging():
    """
    Setups rich logging
    """

    FORMAT = "%(message)s"  # pylint: disable=invalid-name
    logging.basicConfig(
        level="WARNING",
        format=FORMAT,
        datefmt="[%X]",
        handlers=[RichHandler(console=get_console("log"), rich_tracebacks=True)],
    )


def setup_traceback_handler() -> None:
    """Ensure to call this function before importing any invoke modules"""
    install_traceback_handler(show_locals=True, console=get_console("log"))
