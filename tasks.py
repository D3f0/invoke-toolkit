import re
import subprocess
import sys

from invoke_toolkit import Context, task
from rich.prompt import Prompt
from pathlib import Path

REPO_ROOT = Path(
    subprocess.check_output("git rev-parse --show-toplevel", shell="sh")
    .strip()
    .decode()
)


@task(default=True, autoprint=True)
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
    ctx.run(r"rm -rf ./dist/*.{tar.gz,whl}")


@task()
def test(ctx: Context, debug=False, verbose=False, capture_output=True, picked=False):
    """Runs pytest and exposes some commonly used flags"""
    with ctx.cd(REPO_ROOT):
        args = ""
        if debug:
            args = f"{args} --pdb"
        if verbose:
            args = f"{args} -v"
        if not capture_output:
            args = f"{args} -s"
        # Run on tests of changed files
        if picked:
            args = f"{args} --picked"
        ctx.run(f"uv run pytest {args}", pty=True)


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
):
    """
    Run quartodoc with uv
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
        ctx.run(f"uv run quartodoc build {args}")


@task(aliases=["p"])
def docs_preview(ctx: Context):
    with ctx.cd(REPO_ROOT / "docs"):
        ctx.run("quarto preview")
