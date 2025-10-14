import re
import subprocess
import sys

from invoke_toolkit import Context, task
from rich.prompt import Prompt

REPO_ROOT = (
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
def test(ctx: Context, debug=False, verbose=False):
    with ctx.cd(REPO_ROOT):
        args = ""
        if debug:
            args = f"{args} --pdb"
        if verbose:
            args = f"{args} --pdb"

        ctx.run(f"hatch run dev:pytest {args}", pty=True)


@task()
def release(ctx: Context, skip_sync: bool = False) -> None:
    """Creates a release with github client"""
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


@task()
def dummy(ctx: Context):
    with ctx.status("Hello"):
        ctx.run("sleep 1")

    ctx.rich_exit("[bold]Done[/bold]")
    ctx.print("[bold]hello[/bold]")
