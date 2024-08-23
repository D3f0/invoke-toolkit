"""
Invoke tasks for automation, not dependency in this package itself, so they
should be runnable from inv[oke] script installed from pipx.
"""

import importlib
import os
from pathlib import Path
import sys
from typing import List
from invoke import task, Context
import subprocess

REPO_ROOT = (
    subprocess.check_output("git rev-parse --show-toplevel", shell="sh")
    .strip()
    .decode()
)


@task(
    aliases=[
        "t",
    ],
    help={
        "kw": "Keyword arguments",
        "no_capture": "Don't capture stderr/stdout",
        "debug": "Debug failures or errors",
        "markers": "For example -m slow",
    },
)
def test(
    ctx: Context,
    debug=False,
    verbose=False,
    kw: List[str] = [],
    markers_: List[str] = [],
    no_capture: bool = False,
    last_failed: bool = False,
    fail_fast: bool = False,
):
    """Run tests (call py.test)

    It changes to the top level directory of the repo."""
    with ctx.cd(REPO_ROOT):
        args = ""
        if debug:
            args = f"{args} --pdb"
        if verbose:
            args = f"{args} --pdb"
        if kw:
            keyword = " ".join(f"-k {term}" for term in kw)
            args = f"{args} {keyword}"
        if no_capture:
            args = f"{args} -s"
        if markers_:
            markers = " ".join(f"-m {repr(m)}" for m in markers_)
            args = f"{args} {markers}"
        if last_failed:
            args = f"{args} --last-failed"
        if fail_fast:
            args = f"{args} -x"
        ctx.run(f"hatch run dev:pytest {args}", pty=True)


@task()
def clean_dist(ctx: Context):
    """Cleans the dist directory"""
    with ctx.cd(REPO_ROOT):
        ctx.run("rm -rf dist/*")


@task()
def upload(ctx: Context, repository="pypi"): ...


@task(pre=[clean_dist])
def build(ctx: Context) -> str:
    """Builds the whl file with hatch build"""
    ctx.run("hatch build -t wheel", pty=True, out_stream=sys.stderr)
    return ctx.run().stdout.strip()


@task(
    help={
        "install_method": "Allows to use  `wheel`, `source` or  `editable`",
        "clean": "Flag to disable directory cleanup",
        "shell": "Override shell",
    }
)
def temp_env(ctx: Context, install_method="wheel", clean=True, shell=None):
    """Creates a virtual environment"""
    print("Creating temporary directory...", file=sys.stderr)
    temp_dir = ctx.run("mktemp -d").stdout.strip()
    try:
        print(f"Creating virtualenv in {temp_dir}", file=sys.stderr)
        ctx.run(f"python3 -m venv {temp_dir}")

        with ctx.cd(temp_dir):
            if install_method == "wheel":
                ctx.run(f"source bin/activate && pip install {REPO_ROOT}/dist/*.whl")
            elif install_method == "editable":
                ctx.run(f"source bin/activate && pip install -e {REPO_ROOT}")
            elif install_method == "source":
                ctx.run(f"source bin/activate && pip install {REPO_ROOT}")
            else:
                sys.exit(f"Method {install_method} not recognized")

            print("Opening shell", file=sys.stderr)

            shell = shell or Path(os.getenv("SHELL")).name
            if shell == "fish":
                activation_script = "source bin/activate.fish"
            else:
                activation_script = "source bin/activate"
            ctx.run(
                f"$SHELL -c '{activation_script}; $SHELL'",
                pty=True,
                env={"shell": shell},
            )
            print("Deleting environment", file=sys.stderr)
    except Exception as error:
        print(f"task stopped by: {error}")
    if clean:
        ctx.run(f"rm -rf {temp_dir}", pty=True)
    else:
        print(f"Temporary environment left {temp_dir}")


@task(autoprint=True)
def print_module_path(ctx: Context, module=""):
    if not module:
        return ""
    try:
        module = importlib.import_module(name=module)
    except ImportError as error:
        sys.exit(error)

    path = getattr(module, "__path__", None)
    if path is None:
        sys.exit(f"No __path__ for {module}")
    return path[0]


@task()
def test_in_docker(ctx: Context) -> None:
    with ctx.cd(REPO_ROOT):
        tag = "invoke-toolkit:docker-test"
        ctx.run(f"docker build -f scripts/docker/Dockerfile . -t {tag}")
        ctx.run(
            f"docker run --rm -ti -f scripts/docker/Dockerfile . -t {tag}", pty=True
        )
