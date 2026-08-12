"""Main task collection for the local_tasks discovery example.

This example demonstrates how ``local_tasks.py`` is discovered alongside a
project ``tasks.py`` and exposed under the ``local`` namespace.

Run with:
    intk --search-root tests/examples/local_tasks --list
    intk --search-root tests/examples/local_tasks build
    intk --search-root tests/examples/local_tasks local.deploy
"""

from invoke_toolkit import Context, task


@task
def build(ctx: Context) -> None:
    """Build the project (defined in tasks.py)."""
    ctx.print("[green]Building project[/green]")
