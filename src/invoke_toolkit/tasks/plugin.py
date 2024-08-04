from invoke import Context, task


@task(default=True)
def list_(ctx: Context):
    """List plugins"""


@task(default=True)
def add(ctx: Context, plugin_spec: str) -> None:
    """Add a plugin"""


@task(default=True)
def remove(ctx: Context, name: str) -> None:
    """Add a plugin"""
