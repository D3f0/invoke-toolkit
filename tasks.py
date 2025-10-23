import re
from shutil import which
import subprocess
import sys
from pathlib import Path

from rich.prompt import Prompt

from invoke_toolkit import Context, task
from invoke.util import debug

try:
    REPO_ROOT = Path(
        subprocess.check_output("git rev-parse --show-toplevel", shell=True)
        .strip()
        .decode()
    )
except subprocess.SubprocessError:
    REPO_ROOT = Path()


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


@task(
    help={
        "target_": "Target format",
        "output": "Output directory, by default is ./dist/",
    },
    autoprint=True,
)
def build(ctx: Context, target_=[], output="./dist/"):  # pylint: disable=dangerous-default-value
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


@task(
    aliases=["t"],
    help={
        "debug": "Uses [green]pdb[pp][/green] to debug tests, use [bold]sticky[/bold]",
        "verbose": "Run in verbose mode, shows output to stdout",
        "capture_output": "Do not capture output",
        "picked": "Run only changed tests in git",
        "fzf": "Uses fuzzy finder to select which tests to run",
    },
)
def test(
    ctx: Context,
    debug_=False,
    verbose=False,
    capture_output=True,
    picked=False,
    keyword: list[str] = [],
    last_failed: bool = False,
    fzf: bool = False,
    html: bool = False,
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
                "[bold]Ctrl-C[/bold]/[bold]Ctrl-D[/bold] to cancel? "
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
def docs_api_build(
    ctx: Context,
    config: str = "",
    filter_: str = "",
    dry_run: bool = False,
    watch: bool = False,
    verbose: bool = False,
    timeout: int = 0,
):
    """
    Runs uv run quartodoc build with the provided arguments.
    """
    # uv run quartodc build --help
    #   --config TEXT  Change the path to the configuration file.  The default is
    #                  `./_quarto.yml`
    #   --filter TEXT  Specify the filter to select specific files. The default is
    #                  '*' which selects all files.
    #   --dry-run      If set, prevents new documents from being generated.
    #   --watch        If set, the command will keep running and watch for changes
    #                  in the package directory.
    #   --verbose      Enable verbose logging.
    #   --help         Show this message and exit.
    args = ""
    if config:
        args = f"{args} --config {config}"
    if filter_:
        args = f"{args} --filter {filter_}"
    if dry_run:
        args = f"{args} --dry_run"
    if watch:
        args = f"{args} --watch"
    if verbose:
        args = f"{args} --verbose"

    with ctx.cd(REPO_ROOT / "docs"):
        ctx.run(
            f"uv run quartodoc build {args}", timeout=timeout if timeout > 0 else None
        )


@task()
def docs_api_watch_entr(ctx: Context, timeout: int = 5):
    """Uses entr to rebuild, when --watch doesn't detect changes. Requires entr CLI"""
    if not which("entr"):
        ctx.rich_exit("[bold]entr[/bold] not found in [green]$PATH[/green]")
    ctx.run(
        f"""
        git ls-files **/*.py | entr -n {sys.argv[0]} -T {timeout} -e docs-api-build
        """,
        echo=True,
    )


@task(aliases=["p"])
def docs_preview(ctx: Context):
    """
    Runs [green]quarto preview[/green] to visualize the documentation.
    """
    with ctx.cd(REPO_ROOT / "docs"):
        ctx.run("quarto preview")


@task()
def run_in_container(
    ctx: Context,
    image="ghcr.io/astral-sh/uv:trixie",
    container_tool: str = "",
    command: str = "it -l",
    rm: bool = True,
    interactive: bool = True,
    tty: bool = True,
):
    """
    Runs [green]invoke-toolkit[/green] in a container.
    """
    container_tool = "podman"
    volumes = "--volume $PWD:/repo:ro --volume $PWD/tasks.py:/tasks.py"
    flags = ""
    if rm:
        flags = f"{flags} --rm"
    if interactive:
        flags = f"{flags} -i"
    if tty:
        flags = f"{flags} -t"
    ctx.run(
        f"""
        {container_tool} run {flags} -ti {volumes} {image} uv tool run --from /repo/ {command}
        """,
        pty=ctx.config.run.pty,
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


@task()
def env(ctx: Context, clear=False) -> None:
    """([green]re[/green])creates the virtual environment (with [red]uv[/red])"""
    args = ""
    if clear:
        args = f"{args} --clear"
    ctx.run(f"uv venv {args}; uv sync --group dev", pty=True)


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
