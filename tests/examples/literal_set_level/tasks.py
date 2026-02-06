"""Tasks demonstrating Literal type parameter support."""

from typing import Literal

from invoke_toolkit import Context, task


@task()
def set_level(ctx: Context, level: Literal["debug", "info", "error"] | None = None):
    """Set log level from available options."""
    if level:
        print(f"Level: {level}")
