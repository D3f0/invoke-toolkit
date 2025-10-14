"""
Output related helper
"""

import sys
from typing import NoReturn
from .console import get_console


def rich_exit(message: str, *, error_code: int = 1) -> NoReturn:
    """An alternative to sys.exit that has rich output"""
    get_console().log(message)
    sys.exit(error_code)
