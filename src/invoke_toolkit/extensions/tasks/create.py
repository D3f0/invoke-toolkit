"""Plugin handling tasks"""

from pathlib import Path
from textwrap import dedent


from rich.syntax import Syntax

from invoke_toolkit import Context, task

TEMPLATE = r"""\
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


@task(
    aliases=[
        "s",
    ],
)
def script(
    ctx: Context, name: str = "tasks", location: str = ".", runnable=False
) -> None:
    """
    Creates a new script

    ```bash
    ```
    """

    base = Path(location)

    path = base / name
    with ctx.cd(base):
        if not name.endswith(".py"):
            ctx.print_err(f"Adding {name}[bold].py[/bold] suffix")
            name = f"{name}.py"
            path = Path(name)
            if path.exists():
                ctx.rich_exit(f"{name} already exists")
            ctx.rich_exit(
                "For scripts, you need to add the [bold].py[/bold] suffix to the names"
            )
        _ = path.write_text(TEMPLATE, encoding="utf-8")
        content = path.read_text(encoding="utf-8")
        code = Syntax(content, lexer="python")
        ctx.print_err(f"Created script named path {path}")
        ctx.print_err(
            f"You can run it with `uv run {path}`. This file contains the following code"
        )
        ctx.print_err(code)


@task(aliases=["x"])
def add_shebang(ctx: Context, file_: str | Path = "tasks.py"):
    """
    Adds the uv shebang to scripts.

    More info: https://akrabat.com/using-uv-as-your-shebang-line/
    """
    path = Path(file_)
    if not path.is_file():
        ctx.rich_exit(f"[red]{file_}[/red] doesn't exit")
    ctx.print_err(f"Adding shebang to {path}")
    # TODO: Make a backup
    shebang = "#!/usr/bin/env -S uv run --script"
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        lines = [
            "",
        ]
    if lines[0] != shebang:
        new_conetnt_lines = [shebang]
        new_conetnt_lines.extend(lines)
        if lines[-1].strip() != "":
            new_conetnt_lines.append("")
        new_content = "\n".join(new_conetnt_lines)
        path.write_text(new_content, encoding="utf-8")
    else:
        ctx.print(f"{path} has already a shebang")


@task(aliases=["p"])
def package(
    ctx: Context, name: str = "invoke-toolkit-tasks", location: str = "."
) -> None:
    """
    Creates a package for tasks. When the package is installed with invoke-toolkit
    its collections will be automatically made available
    """
    ctx.print_err("Package mode is still in development")
    # TODO: Create a package
    # TODO: Update the TOML to include the the entrypoints
    # TODO: Create github repo maybe?
    base = Path(location)

    pyproject_here = base / "pyproject.toml"
    if pyproject_here.exists():
        ctx.rich_exit(
            dedent(
                """
                Can't create a package here because a pyproject.toml already exists
                Try changing the [bold]--location[/bold] parameter.
                """
            ).strip()
        )
    pkg_creation = ctx.run(f"uv init --lib {name}", warn=True)
    if not pkg_creation.ok:
        ctx.rich_exit(f"Problems creating the package {name}")
    _ = Path(f"./src/{name}")
