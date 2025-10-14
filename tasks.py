from invoke import task, Context
import subprocess

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
def build(ctx: Context, target_=[], output="./dist/"):
    """Builds distributable package"""
    args = ""
    if target_:
        target = " ".join(f"-t {t}" for t in target_)
        args = f"{args} {target}"
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
def clean_dist(ctx: Context):
    with ctx.cd(REPO_ROOT):
        ctx.run("dist/*")
