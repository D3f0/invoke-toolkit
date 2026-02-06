"""Tasks demonstrating enum parameter support."""

from enum import Enum

from invoke_toolkit import Context, task


class Size(str, Enum):
    """Size enumeration."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


@task()
def select_size(ctx: Context, size: Size | None = None):
    """Select a size from available options."""
    if size:
        print(type(size))
