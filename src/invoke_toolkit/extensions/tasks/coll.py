"""Plugin handling tasks"""

from pathlib import Path
from invoke_toolkit import Context, task
from rich.syntax import Syntax

TEMPLATE = r"""
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "invoke-toolkit==0.0.26",
# ]
# ///

from invoke_toolkit import task, Context, script

@task()
def hello_world(ctx: Context):
    ctx.run("echo 'hello world'")

script()
"""


@task(aliases=["n", "new"])
def init(
    ctx: Context,
    name="tasks.py",
    script=False,
    package=False,
):
    """
    Creates a new script that can be run with [bold]uv run my_script.py[/bold].

    ```bash
    ```
    """

    path = Path(name)
    if path.exists():
        ctx.rich_exit(f"{name} already exists")
    if script and package:
        ctx.rich_exit("You can only use a mode at a time, script or package")
    elif not script and not package:
        ctx.print(f"[grey]Assuming [bold]script[/bold] mode for {name}[/grey]")
        script = True
    if script:
        if not name.endswith(".py"):
            ctx.rich_exit(
                "For scripts, you need to add the [bold].py[/bold] suffix to the names"
            )
        path.write_text(TEMPLATE, encoding="utf-8")
        content = path.read_text(encoding="utf-8")
        code = Syntax(content, lexer="python")
        ctx.print_err(f"Created script named path {path}")
        ctx.print_err(
            f"You can run it with `uv run {path}`. This file contains the following code"
        )
        ctx.print_err(code)

    elif package:
        ...
