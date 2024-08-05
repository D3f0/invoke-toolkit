from invoke import task, Context
import subprocess

REPO_ROOT = (
    subprocess.check_output("git rev-parse --show-toplevel", shell="sh")
    .strip()
    .decode()
)


@task()
def build(ctx: Context):
    ctx.run("hatch build", pty=True)


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
