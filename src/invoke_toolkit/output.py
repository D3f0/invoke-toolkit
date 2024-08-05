from rich.console import Console
import sys

console = Console(file=sys.stderr)


def rich_exit(reason: str, exit_code: int = 1):
    """A replacement of sys.exit that support rich formatting"""
    console.print(reason)
    sys.exit(exit_code)
