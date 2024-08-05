"""
Generate self contained distributable scripts
"""

from invoke import task, Context


@task(default=True)
def build(ctx: Context):
    """Builds a package"""
