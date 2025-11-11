"""Plugin handling tasks"""

from pathlib import Path
from textwrap import dedent

from rich.syntax import Syntax

from invoke_toolkit import Context, task

try:
    from copier import run_copy
except ImportError:
    run_copy = None  # type: ignore[assignment]

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
    ctx: Context,
    name: str = "my-tasks-package",
    location: str = ".",
) -> None:
    """
    Creates a package for tasks using the invoke-toolkit copier template.
    When installed, the package's collections will be automatically discovered.

    The generated package includes entry-point annotations that allow
    invoke-toolkit to discover and load the tasks collection.
    """
    if run_copy is None:
        ctx.rich_exit(
            "copier is required to create packages. "
            "Install it with: uv pip install copier"
        )

    base = Path(location)
    target_path = base / name

    if target_path.exists():
        ctx.rich_exit(
            dedent(
                f"""
                Can't create package: {target_path} already exists.
                Try changing the [bold]--name[/bold] or [bold]--location[/bold] parameter.
                """
            ).strip()
        )

    # Find the copier template in the invoke-toolkit package
    try:
        import invoke_toolkit  # pylint: disable=import-outside-toplevel

        # Try to find templates relative to the invoke_toolkit module
        # This works for both development (repo root) and installed packages
        invoke_toolkit_path = Path(invoke_toolkit.__file__).parent

        # First try: templates in the same directory (development setup)
        template_path = (
            invoke_toolkit_path.parent.parent / "templates" / "package-template"
        )

        # Second try: templates in the package data directory (installed)
        if not template_path.exists():
            template_path = invoke_toolkit_path / "templates" / "package-template"

        # Third try: check if we're in a site-packages installation
        if not template_path.exists():
            # Look for templates in the package root's share or data directory
            site_packages_parent = invoke_toolkit_path.parent.parent.parent
            template_path = site_packages_parent / "templates" / "package-template"
    except (ImportError, AttributeError) as exc:
        ctx.rich_exit(f"Could not find invoke-toolkit installation: {exc}")

    if not template_path.exists():
        ctx.rich_exit(
            dedent(
                f"""
                Template directory not found at [bold]{template_path}[/bold].
                Please ensure invoke-toolkit is properly installed.
                """
            ).strip()
        )

    ctx.print_err(
        f"[blue]Creating package[/blue] [bold]{name}[/bold] [blue]from template...[/blue]"
    )

    try:
        # Prepare data for template rendering
        package_slug = name.lower().replace("-", "_").replace(" ", "_")
        template_data = {
            "package_name": name,
            "package_slug": package_slug,
            "collection_name": package_slug,
        }

        run_copy(
            src_path=str(template_path),
            dst_path=str(target_path),
            data=template_data,
            quiet=False,
            unsafe=True,
            defaults=True,
            skip_tasks=True,
        )
        ctx.print_err(f"[green]✓ Package created at[/green] [bold]{target_path}[/bold]")
        ctx.print_err(
            dedent(
                f"""
                [yellow]Next steps:[/yellow]
                  cd {target_path}
                  uv sync
                  uv pip install -e .
                """
            ).strip()
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        ctx.rich_exit(f"Failed to create package: {exc}")
