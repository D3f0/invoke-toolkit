"""Project-local tasks for the local_tasks discovery example.

These tasks are discovered from ``local_tasks.py`` next to ``tasks.py`` and are
added under the ``local`` namespace (for example ``local.deploy``). Keeping them
here lets you separate machine- or checkout-specific tasks from the shared
``tasks.py`` collection.
"""

from invoke_toolkit import Context, task


@task
def deploy(ctx: Context) -> None:
    """Deploy the project (defined in local_tasks.py)."""
    ctx.print("[cyan]Deploying project from local tasks[/cyan]")
