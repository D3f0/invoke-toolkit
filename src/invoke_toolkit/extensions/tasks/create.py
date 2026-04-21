"""Plugin handling tasks"""

import hashlib
import json
import re
import subprocess
from pathlib import Path
from shutil import which
from textwrap import dedent
from typing import Any

import platformdirs
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table
from typing_extensions import Annotated

import invoke_toolkit
from invoke_toolkit import Context, __version__, task
from invoke_toolkit.loader.entrypoint import COLLECTION_ENTRY_POINT, PLUGIN_PREFIX

try:
    from copier import run_copy
except ImportError:
    run_copy = None  # type: ignore[assignment]


# Git config key for custom template repository/path
GIT_CONFIG_TEMPLATE_KEY = "invoke-toolkit.package-template"


def _get_git_config_value(key: str) -> str | None:
    """
    Get a value from git config.

    Args:
        key: The git config key to look up

    Returns:
        The config value if found, None otherwise
    """
    try:
        result = subprocess.run(
            ["git", "config", "--get", key],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


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
    # requires-python = ">=3.11"
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
    ctx: Context,
    name: Annotated[str, "Script name"] = "tasks",
    location: Annotated[str, "Location to create the script"] = ".",
    runnable=False,
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
def add_shebang(
    ctx: Context,
    file_: Annotated[str | Path, "Path to the file to add shebang to"] = "tasks.py",
):
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


def _get_default_template_path() -> Path:
    """
    Get the default template path from the invoke-toolkit package.

    Returns:
        Path to the bundled package-template directory
    """
    # Try to find templates relative to the invoke_toolkit module
    # This works for both development (repo root) and installed packages
    invoke_toolkit_path = Path(invoke_toolkit.__file__).parent

    # First try: templates in the same directory (development setup)
    template_path = invoke_toolkit_path.parent.parent / "templates" / "package-template"

    # Second try: templates in the package data directory (installed)
    if not template_path.exists():
        template_path = invoke_toolkit_path / "templates" / "package-template"

    # Third try: check if we're in a site-packages installation
    if not template_path.exists():
        # Look for templates in the package root's share or data directory
        site_packages_parent = invoke_toolkit_path.parent.parent.parent
        template_path = site_packages_parent / "templates" / "package-template"

    return template_path


def _resolve_template_source(template: str | None, ctx: Context) -> str:
    """
    Resolve the template source path/URL.

    Priority:
    1. Explicit --template parameter
    2. Git config (invoke-toolkit.package-template)
    3. Default bundled template

    Args:
        template: Explicit template path/URL from --template parameter
        ctx: Context for error reporting

    Returns:
        Template path or URL to use with copier
    """
    # Priority 1: Explicit --template parameter
    if template:
        ctx.print_err(f"[blue]Using template from --template:[/blue] {template}")
        return template

    # Priority 2: Git config
    git_template = _get_git_config_value(GIT_CONFIG_TEMPLATE_KEY)
    if git_template:
        ctx.print_err(
            f"[blue]Using template from git config ({GIT_CONFIG_TEMPLATE_KEY}):[/blue] {git_template}"
        )
        return git_template

    # Priority 3: Default bundled template
    default_path = _get_default_template_path()
    if not default_path.exists():
        ctx.rich_exit(
            dedent(
                f"""
                Template directory not found at [bold]{default_path}[/bold].
                Please ensure invoke-toolkit is properly installed.

                You can also specify a custom template using:
                  --template <path-or-git-url>
                Or set a default in git config:
                  git config --global {GIT_CONFIG_TEMPLATE_KEY} <path-or-git-url>
                """
            ).strip()
        )

    return str(default_path)


@task(aliases=["p"])
def package(
    ctx: Context,
    name: Annotated[str, "The package name"] = "my-tasks-package",
    location: Annotated[str, "The location to create the package"] = ".",
    ext_name: Annotated[
        str,
        "Optional short name for the extension. If provided, the full package name will be prefixed with 'invoke-toolkit-'",
    ] = "",
    template: Annotated[
        str,
        "Custom copier template path or git URL. If not provided, uses git config "
        f"'{GIT_CONFIG_TEMPLATE_KEY}' or the bundled template.",
    ] = "",
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

    # Check if the location is inside a git repository
    try:
        result = subprocess.run(
            ["git", "-C", str(base), "rev-parse", "--git-dir"],
            capture_output=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            ctx.rich_exit(
                dedent(
                    f"""
                    Can't create package: {base} is inside a git repository.
                    Please choose a location outside of any git repository.
                    """
                ).strip()
            )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # If git is not available or times out, continue anyway
        pass

    # Determine the actual package name
    if ext_name:
        actual_name = f"invoke-toolkit-{ext_name}"
    else:
        actual_name = name

    target_path = base / actual_name

    if target_path.exists():
        ctx.rich_exit(
            dedent(
                f"""
                Can't create package: {target_path} already exists.
                Try changing the [bold]--name[/bold] or [bold]--location[/bold] parameter.
                """
            ).strip()
        )

    # Resolve the template source (explicit param, git config, or default)
    template_source = _resolve_template_source(template or None, ctx)

    ctx.print_err(
        f"[blue]Creating package[/blue] [bold]{actual_name}[/bold] [blue]from template...[/blue]"
    )

    try:
        # Prepare data for template rendering
        package_slug = actual_name.lower().replace("-", "_").replace(" ", "_")

        # Determine extension short name for entry point
        if actual_name.startswith(PLUGIN_PREFIX):
            extension_short_name = actual_name[len(PLUGIN_PREFIX) :]
        else:
            extension_short_name = package_slug

        template_data = {
            "package_name": actual_name,
            "package_slug": package_slug,
            "collection_name": extension_short_name,
            "extension_short_name": extension_short_name,
            "python_version": "3.11",
        }

        run_copy(
            src_path=template_source,
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
                  # Test your package
                  uv run --directory {target_path} -m invoke-toolkit -l
                """
            ).strip()
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        ctx.rich_exit(f"Failed to create package: {exc}")


@task(aliases=["debug-ep", "d"])
def debug_entrypoints(
    ctx: Context,
    format_: Annotated[str, "Output format (table or json)"] = "table",
    output: Annotated[
        str, "Output file path (optional). If provided, JSON output is written to file."
    ] = "",
) -> None:
    """
    Show invoke-toolkit entry points.

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
def script_env(
    ctx: Context,
    script_file: Annotated[str, "Path to the script file"] = "",
) -> str:
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
