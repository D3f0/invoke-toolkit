from invoke import Context, task


@task(default=True)
def list_(ctx: Context):
    """List plugins"""


@task()
def add(ctx: Context, plugin_spec: str) -> None:
    """Add a plugin"""


@task()
def remove(ctx: Context, name: str) -> None:
    """Add a plugin"""
