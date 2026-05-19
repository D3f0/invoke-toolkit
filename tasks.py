# pyright: ignore[reportMissingParameterType]

import json
import re
import subprocess
import sys
from pathlib import Path
from shutil import which
from typing import Annotated, Any

from invoke.runners import Result
from invoke.util import debug
from rich.prompt import Prompt

from invoke_toolkit import Context, task

try:
    _repo_root = Path(
        subprocess.check_output("git rev-parse --show-toplevel", shell=True)
        .strip()
        .decode()
    )
except subprocess.SubprocessError:
    _repo_root = Path()

REPO_ROOT: Path = _repo_root


@task(default=True, autoprint=True, aliases=["v"])
def version(
    ctx: Context,
):
    """Shows package version (git based)"""
    with ctx.cd(REPO_ROOT):
        with ctx.status("Computing version from SCM"):
            return ctx.run(
                "uvx --with uv-dynamic-versioning hatchling version",
                hide=not ctx.config.run.echo,
            ).stdout.strip()


@task(autoprint=True)
def build(
    ctx: Context,
    target_: Annotated[list, "Target format"] = [],  # pylint: disable=dangerous-default-value
    output: Annotated[str, "Output directory, by default is ./dist/"] = "./dist/",
):
    """Builds distributable package"""
    with ctx.cd(REPO_ROOT):
        args = ""
        if isinstance(target_, list):
            target = " ".join(f"-t {t}" for t in target_)
            args = f"{args} {target}"
        elif target_:
            args = f"{args} -t {target_}"
        if output:
            args = f"{args} -d {output}"

        return ctx.run(
            f"uvx --with uv-dynamic-versioning hatchling build {args}",
            hide=not ctx.config.run.echo,
        ).stderr.strip()


@task()
def clean(ctx: Context):
    """Cleans dist"""
    with ctx.cd(REPO_ROOT):
        ctx.run(r"rm -rf ./dist/*.{tar.gz,whl}")


@task()
def show_package_files(ctx: Context, file_type="whl"):
    """Shows the contents of the latest package"""
    with ctx.cd(REPO_ROOT / "dist"):
        ls = ctx.run(f"ls -t *.{file_type}", warn=True, echo=ctx.config.run.echo)
        if not ls.ok:
            ctx.rich_exit(
                f"Couldn't find any package files of type [red]{file_type}[/red]"
            )
        newest_pkg, *_ = ls.stdout.splitlines()
        ctx.run(f"tar tvf {newest_pkg}")


@task(aliases=["t"])
def test(
    ctx: Context,
    debug_: Annotated[
        bool, "Uses [green]pdb[pp][/green] to debug tests, use [bold]sticky[/bold]"
    ] = False,
    verbose: Annotated[bool, "Run in verbose mode, shows output to stdout"] = False,
    capture_output: Annotated[bool, "Do not capture output"] = True,
    picked: Annotated[bool, "Run only changed tests in git"] = False,
    keyword: Annotated[list[str], ""] = [],  # pylint: disable=dangerous-default-value
    last_failed: Annotated[bool, ""] = False,
    fzf: Annotated[bool, "Uses fuzzy finder to select which tests to run"] = False,
    html: Annotated[bool, ""] = False,
):
    """Runs [green]pytest[/green] and exposes some commonly used flags"""
    with ctx.cd(REPO_ROOT):
        args = ""
        if debug_:
            args = f"{args} --pdb"
        if verbose:
            args = f"{args} -v"
        if not capture_output:
            args = f"{args} -s"
        # Run on tests of changed files
        if picked:
            args = f"{args} --picked"
        if keyword:
            kw = " ".join(f"-k {kw}" for kw in keyword)
            args = f"{args} {kw}"
        if last_failed:
            args = f"{args} --last-failed"
        if html:
            # addopts = "--html=report.html --self-contained-html"
            args = f"{args} --html=report.html --self-contained-html"
        if fzf:
            # Select the tests with fzf
            if not which("fzf"):
                ctx.rich_exit("[bold]fzf[/bold] not found")
            if which("bat"):
                debug("Running with bat")
                preview_cmd = r"bat --color always {}"
            else:
                debug("Preview with cat")
                preview_cmd = r"cat {}"
            test_to_run = ctx.run(
                f"""
                find ./tests/ -name 'test_*.py' | fzf --preview '{preview_cmd}'
                """
            ).stdout.strip()
            if not test_to_run:
                ctx.rich_exit("No tests selected 😭")
            else:
                args = f"{args} {test_to_run}"

        run = ctx.run(f"uv run pytest {args}", pty=True, warn=True)
        if html:
            ctx.run("test -f report.html && open report.html")
        if not run.ok:
            ctx.rich_exit("test failed", exit_code=run.return_code)


@task()
def release(ctx: Context, skip_sync: bool = False) -> None:
    """
    Tags (if the git repo is [bold]clean[/bold]) proposing the next tag
    Pushes the tag to [bold]github[/bold]
    Creates a release
    """
    if not skip_sync:
        with ctx.status("Syncing tags 🏷️ "):
            ctx.run("git fetch --tags")

    with ctx.status("Getting existing tags 👀 "):
        git_status = ctx.run(
            "git status --porcelain ", warn=True, hide=not ctx.config.run.echo
        )
    if git_status.stdout:
        sys.exit(f"The repo has changes: \n{git_status.stdout}")
    tags = [
        tag.strip("v")
        for tag in ctx.run(
            # "git tag --sort=-creatordate",
            "git tag --sort=-creatordate | sed -e 's/^v//g' | sort -r",
            hide=not ctx.config.run.echo,
        ).stdout.splitlines()
    ]

    def compare(dotted_version: str) -> tuple[int, int, int]:
        major, minor, patch, *_ = dotted_version.split(".")
        return int(major), int(minor), int(patch)

    tags.sort(key=compare, reverse=True)

    most_recent_tag, *_rest = tags
    major_minor, patch = most_recent_tag.rsplit(".", maxsplit=1)
    patch_integer = int(patch) + 1
    next_tag_version = f"v{major_minor}.{patch_integer}"

    while True:
        try:
            user_input = Prompt.ask(
                f"New tag [blue]{next_tag_version}[/blue] "
                + "[bold]Ctrl-C[/bold]/[bold]Ctrl-D[/bold] to cancel? "
            )
        except EOFError:
            sys.exit("User cancelled")
        if not user_input:
            break
        if re.match(r"v?\d\.\d+\.\d+", user_input):
            break

    ctx.print("[blue]Creating tag...")
    ctx.run(f"git tag {next_tag_version}")
    ctx.run("git push origin --tags")
    ctx.print("[blue]Pushing tag...[/blue]")
    ctx.print("[bold]OK[/bold]")
    clean(ctx)
    build(ctx, target_="wheel")

    ctx.print("Creating the release on github")

    subprocess.run(
        f"gh release create {next_tag_version} ./dist/*.whl",
        shell=True,
        check=True,
    )


@task(aliases=["b"])
def docs_build(ctx: Context):
    """
    Builds documentation with [green]zensical[/green].
    """
    with ctx.cd(REPO_ROOT):
        ctx.run("uv run --group doc zensical build")


@task(aliases=["p"])
def docs_serve(ctx: Context):
    """
    Serves documentation locally with [green]zensical[/green].
    """
    with ctx.cd(REPO_ROOT):
        ctx.run("uv run --group doc zensical serve", pty=True)


@task()
def docs_watch(ctx: Context):
    """Uses entr to rebuild docs when source files change. Requires entr CLI"""
    with ctx.cd(REPO_ROOT):
        if not which("entr"):
            ctx.rich_exit("[bold]entr[/bold] not found in [green]$PATH[/green]")
        ctx.run(
            f"""
            git ls-files **/*.py | entr -n {sys.argv[0]} docs-build
            """,
            echo=True,
        )


@task(autoprint=True)
def find_container_tool(ctx: Context) -> str:
    """Checks which container tool is available (docker, podman, nerdctl)"""
    known_tools = ["docker", "podman", "nerdctl", "nerdctl.lima"]
    results: dict[str, Any] = {}
    for tool in known_tools:
        promise: Any = ctx.run(
            f"which {tool} && {tool} ps </dev/null",
            asynchronous=True,
            warn=True,
            in_stream=False,
        )
        results[tool] = promise
    for tool, promise in results.items():
        result: Result = promise.join()
        debug(f"{tool}: {result}")

        if result.ok:
            return tool
    return ctx.rich_exit("No container tool found")


@task()
def run_in_container(  # pylint: disable=too-many-locals
    ctx: Context,
    image: Annotated[
        str, "Base image, should contain uv"
    ] = "ghcr.io/astral-sh/uv:trixie",
    container_tool: Annotated[str, "docker, podman, nerdctl or nerdctl.lima"] = "",
    command: Annotated[str, "The command to run, e.g. bash"] = "intk -l",
    rm: Annotated[bool, "Delete container at exit"] = True,
    interactive: Annotated[bool, "Run interactively"] = True,
    volumes: Annotated[list[str], "Extra list of volumes"] = [],  # pyright: ignore[reportCallInDefaultInitializer]
    tty: bool = True,
    workdir: Annotated[str, "Working directory"] = "/foo",
    with_: Annotated[list[str], "Extra packages to install with uv"] = [],  # pyright: ignore[reportCallInDefaultInitializer]
):
    """
    Runs [green]invoke-toolkit[/green] in a container.

    The command will be run with [bold]uv tool run --from /repo[/] [green]{command}[/green]
    """
    container_tool = container_tool or find_container_tool(ctx)
    volumes = ["$PWD:/repo:ro", "$PWD/tasks.py:/tasks.py"]
    flags = ""
    if rm:
        flags = f"{flags} --rm"
    if interactive:
        flags = f"{flags} -i"
    if tty:
        flags = f"{flags} -t"
    if workdir:
        flags = f"{flags} -w {workdir}"
    if volumes:
        cli_vol_args = " ".join(f"-v {vol_expr}" for vol_expr in volumes)
        flags = f"{flags}  {cli_vol_args}"

    uv_tool_flags = ""
    if with_:
        with_args = [f"--with {pkg}" for pkg in with_]
        uv_tool_flags = f"{uv_tool_flags} {' '.join(with_args)}"

    ctx.run(
        f"{container_tool} run {flags} {image} "
        + f"uv tool run {uv_tool_flags} --from /repo/ {command}",
        # pty=ctx.config.run.pty,
        pty=True,
    )


@task(pre=[clean, build])
def publish(ctx: Context):
    """
    Build and publish to PyPI using a token.

    [red]TODO:[/red] This should be a github action with trusted publishing
    """
    ctx.run(
        """
        test -n PYPI_PASSWORD && uv publish -t $PYPI_PASSWORD
        """
    )


@task(aliases=["env", "setup"])
def venv(ctx: Context, clear: bool = False) -> None:
    """([green]re[/green])creates the virtual environment (with [red]uv[/red])"""
    args = ""
    if clear:
        args = f"{args} --clear"
    ctx.run(f"uv venv {args}; uv sync --all-extras --all-groups", pty=True)


@task()
def type_check(ctx: Context, all_files=False):
    """
    Performs type checks, [bold]not yet included in pre-commit[/bold]
    """
    args = ""
    if not all_files:
        # get staged files
        staged_files = ctx.run("git diff --name-only --cached").stdout.splitlines()

        args = f"{args} {' '.join(staged_files)}"
    args = ""
    ctx.run(
        f"""
        uv run --with pyrefly pyrefly check {args}
        """,
        pty=True,  # Colors 🎨
    )


@task()
def plugin_clean(ctx: Context):
    """Cleans up packages used as plugins"""
    with ctx.cd(REPO_ROOT):
        packages: list[dict[str, str]] = json.loads(
            ctx.run("uv pip list --format json", hide=not ctx.config.run.echo).stdout
        )
        editables = [
            package_info
            for package_info in packages
            if "editable_project_location" in package_info
            and not package_info["editable_project_location"] == str(REPO_ROOT)
        ]
        for pkg in editables:
            name = pkg["name"]
            ctx.run(f"uv pip uninstall {name}")
