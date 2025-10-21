"""Plugin handling tasks"""

from invoke import Context, task

config = {"a": 1}


@task(default=True, name="list")
def list_(ctx: Context, flag=True):
    """List all the collections available to invoke-toolkit"""


@task()
def add(ctx: Context, plugin_spec: str) -> None:
    """Adds a collection from a local path or a remote git repository"""


@task()
def remove(ctx: Context, name: str) -> None:
    """Removes a collection previously added with collections.add"""
