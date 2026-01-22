"""Plugin handling tasks"""

import hashlib
import json
import re
from pathlib import Path
from shutil import which
from textwrap import dedent
from typing import Any

import platformdirs
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

import invoke_toolkit
from invoke_toolkit import Context, __version__, task
from invoke_toolkit.loader.entrypoint import COLLECTION_ENTRY_POINT

try:
    from copier import run_copy
except ImportError:
    run_copy = None  # type: ignore[assignment]


def _get_template() -> str:
    """Generate template with current invoke-toolkit version"""
    # Use >= specifier for all versions to allow flexibility when installing
    # from different sources (e.g., git checkout, local editable installs)
    match = re.search(r"(?P<prod_ver>\d+\.\d+\.\d+)", __version__)
    prod_ver = match.group("prod_ver") if match else __version__
    version_specifier = f">={prod_ver}"
    version_for_template = version_specifier
    script_template = dedent(rf"""
    #!/usr/bin/env -S uv run --script
    # /// script
    # requires-python = ">=3.10"
    # dependencies = [
    #     "invoke-toolkit{version_for_template}",
    # ]
    # ///

    from invoke_toolkit import task, Context, script

    @task()
    def hello_world(ctx: Context):
        ctx.run("echo 'hello world'")

    script()
    """)

    return script_template.lstrip("\n")


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
        template_content = _get_template()
        _ = path.write_text(template_content, encoding="utf-8")
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
            "Install it with: uv pip install invoke-toolkit[copier]"
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
            "python_version": "3.10",
        }

        run_copy(
            src_path=str(template_path),
            dst_path=str(target_path),
            data=template_data,
            quiet=False,
            unsafe=True,
            defaults=True,
            skip_tasks=True,
            overwrite=True,
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


@task(aliases=["debug-ep", "d"])
def debug_entrypoints(
    ctx: Context,
    format_: str = "table",
    output: str = "",
) -> None:
    """
    Show invoke-toolkit entry points.

    Args:
        format_: Output format (table or json). Default: table
        output: Output file path (optional). If provided, JSON output is written to file.

    Examples:
        intk create.debug-entrypoints
        intk create.debug-entrypoints --format json
        intk create.debug-entrypoints --format json --output entrypoints.json
    """
    console = Console()

    entry_points_dict: dict[str, Any] = {}

    try:
        from importlib.metadata import (  # pylint: disable=import-outside-toplevel
            entry_points as get_entry_points,
        )

        eps = get_entry_points()

        if hasattr(eps, "select"):
            # Python 3.10+
            group = eps.select(group=COLLECTION_ENTRY_POINT)
        else:
            # Python 3.9
            group = list(eps.get(COLLECTION_ENTRY_POINT, []))  # pylint: disable=no-member

        for ep in group:
            entry_points_dict[ep.name] = {
                "name": ep.name,
                "value": ep.value,
            }

    except Exception as e:  # pylint: disable=broad-exception-caught
        console.print(f"[red]Error loading entry points: {e}[/red]")
        return

    if not entry_points_dict:
        console.print("[yellow]No entry points found[/yellow]")
        return

    if format_.lower() == "json":
        json_output = json.dumps(entry_points_dict, indent=2)
        if output:
            # Write to file
            try:
                output_path = Path(output)
                output_path.write_text(json_output, encoding="utf-8")
                console.print(f"[green]✓[/green] Entry points written to {output_path}")
            except Exception as e:  # pylint: disable=broad-exception-caught
                console.print(f"[red]Error writing to file: {e}[/red]")
        else:
            # Print to stdout
            console.print(json_output)
    else:
        # Table output (default)
        table = Table(title=f"Entry Points: {COLLECTION_ENTRY_POINT}")
        table.add_column("Name", style="cyan")
        table.add_column("Value", style="magenta")

        for name, info in entry_points_dict.items():
            table.add_row(name, info["value"])

        console.print(table)


@task()
def script_env(ctx: Context, script_file: str = "") -> str:
    """
    Create a [bold]venv[/] for a script to be used with text editor/IDE.

    It should read the script PEP723 section and based on the file path construct
    a virtualenv with uv and installing/updating the dependencies.

    The environment location should be computed from the script path and using platformdirs
    """

    if not script_file:
        ctx.rich_exit("--script parameter is required")

    script_path = Path(script_file).resolve()
    if not script_path.exists():
        ctx.rich_exit(f"Script not found: {script_path}")

    # Read the script content
    script_content = script_path.read_text(encoding="utf-8")

    # Extract PEP 723 inline script metadata (dependencies block)
    # Format: # /// script\n# dependencies = [...]\n# ///
    pep723_pattern = r"# /// script\n(.*?)# ///"
    match = re.search(pep723_pattern, script_content, re.DOTALL)

    dependencies = []
    if not match:
        ctx.rich_exit(f"No script metadata found in {script_path}")
    else:
        metadata_block = match.group(1)
        # Extract dependencies list
        deps_pattern = r"# dependencies = \[(.*?)\]"
        deps_match = re.search(deps_pattern, metadata_block, re.DOTALL)
        if deps_match:
            deps_str = deps_match.group(1)
            # Parse individual dependencies (quoted strings)
            dependencies = re.findall(r'["\']([^"\']+)["\']', deps_str)

    # Compute stable environment location based on script path
    script_hash = hashlib.sha256(str(script_path).encode()).hexdigest()[:16]
    env_name = f"{script_path.stem}-{script_hash}"

    # Use platformdirs to get a stable cache directory
    cache_dir = Path(platformdirs.user_cache_dir("invoke-script-envs"))
    env_path = cache_dir / env_name

    # Ensure cache directory exists
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Check if uv is available
    if not which("uv"):
        ctx.rich_exit("uv is not installed. Please install uv first.")

    # Create or update the virtual environment
    with ctx.status(f"Creating/updating virtual environment at {env_path}"):
        if not env_path.exists():
            ctx.run(f"uv venv {env_path}", hide=not ctx.config.run.echo)

        # Install/update dependencies if any
        if dependencies:
            deps_str = " ".join(dependencies)
            with ctx.status(f"Installing dependencies: {deps_str}"):
                ctx.run(
                    f"uv pip install --python {env_path}/bin/python {deps_str}",
                    hide=not ctx.config.run.echo,
                )

    return str(env_path)
