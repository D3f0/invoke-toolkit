#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "invoke_toolkit",
# ]
# ///

from invoke_toolkit.program import script
from invoke import task, Context


@task()
def hello(ctx: Context):
    print("hello")


script()
