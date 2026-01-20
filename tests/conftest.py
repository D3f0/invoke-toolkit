import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent
from typing import Protocol

import attrs
import pytest

# from invoke.context import Context
from invoke_toolkit import Context


@pytest.fixture
def ctx() -> Context:
    """
    Returns invoke context
    """
    c = Context()
    # Prevent using sys.stdin in pytest
    c.config["run"]["in_stream"] = False
    return c


@pytest.fixture
def git_root(ctx) -> str:
    """Returns the project top level folder (where the git project is cloned)"""
    folder = Path(__file__).parent
    return ctx.run(
        f"git -C {folder} rev-parse --show-toplevel",
    ).stdout.strip()


@pytest.fixture()
def venv(ctx: Context, tmp_path: Path):
    """Creates a virtual environment"""
    version_info = sys.version_info
    version = f"{version_info.major}.{version_info.minor}"
    with ctx.cd(tmp_path):
        ctx.run(f"uv venv --python {version}")
        yield tmp_path


@pytest.fixture
def package_in_venv(git_root, ctx: Context, venv: Path) -> None:
    """A virtual environment in a temporary directory with the package"""
    ctx.run(f"uv pip install --editable {git_root}")


@pytest.fixture(autouse=True)
def clean_consoles():
    """Resets the console manager"""
    from invoke_toolkit.output.console import (
        manager,  # pylint: disable=import-outside-toplevel
    )

    manager._consoles = {}  # pylint: disable=protected-access


@pytest.fixture
def task_in_tmp_path(tmp_path: Path):
    """Creates a tasks.py in tmp_path to run the Program"""
    with open(tmp_path / "tasks.py", mode="w", encoding="utf-8") as fp:
        fp.write(
            dedent(
                """
                from invoke_toolkit import task, Context

                @task()
                def a_task(ctx: Context):
                    ctx.run("echo 'hello'")

                """
            )
        )


@attrs.define
class TempVenv:
    """A temporary virtual environment class that exposes a uv environment.

    It's created by the temp_venv fixture. Has add_package method"""

    path: Path

    def add_package(self, package: str | Path, editable: bool = False) -> None:
        """Installs a package in the temporary virtual environment"""
        args = ""
        if editable:
            args = f"{args} --editable"
        install_result = self._call(f"uv pip install {args} {package}")
        assert install_result.returncode == 0, (
            f"Couldn't install {package} into temp environment"
        )

    def packages(self) -> dict[str, str | dict[str, str]]:
        result = self._call("uv pip list --format json")
        stdout = result.stdout
        decoded = stdout.decode()
        pip_list: list[dict[str, str]] = json.loads(decoded)

        return {p["name"]: p for p in pip_list}

    @property
    def _uv_venv(self) -> dict[str, str]:
        env: dict[str, str] = dict(os.environ.items())
        env.update(VIRTUAL_ENV=str(self.path))
        return env

    def _call(
        self, command: str, cwd: Path | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        """Internal call to the process"""
        result = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self._uv_venv,
            cwd=cwd,
            check=False,
        )
        # assert result.returncode == 0
        return result

    def run(
        self, command: str, cwd: Path | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        """Runs a command in the virtual environment"""
        return self._call(f"uv run {command}", cwd=cwd)

    def __repr__(self):
        return f"<temp venv at {self.path}>"


@pytest.fixture()
def temp_venv(tmp_path_factory, monkeypatch: pytest.MonkeyPatch) -> TempVenv:
    """
    Creates a new temporary virtual environment in isolation

    Returns a wrapper class that interacts allows you to interact with the virtual env
    """
    tmp_path = tmp_path_factory.mktemp("venv")
    version_info = sys.version_info
    version = f"{version_info.major}.{version_info.minor}"
    proc = subprocess.run(
        f"uv venv .venv --python={version}",
        cwd=tmp_path,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 0, "Can't create a virtual environment"
    venv_path = tmp_path / ".venv"
    monkeypatch.setenv("VIRTUAL_ENV", str(venv_path))
    return TempVenv(venv_path)


@pytest.fixture
def suppress_stderr_logging():
    """Remove logging handlers to prevent stderr output"""
    logger = logging.getLogger()
    handlers = logger.handlers[:]

    for handler in handlers:
        logger.removeHandler(handler)

    yield

    for handler in handlers:
        logger.addHandler(handler)


class ShellRunTmp(Protocol):  # pylint: disable=too-few-public-methods
    def __call__(
        self, command: str, cwd: Path | str | None = None
    ) -> subprocess.CompletedProcess[str]: ...


@pytest.fixture
def shell_run_tmp(
    tmp_path_factory: pytest.TempPathFactory,
) -> ShellRunTmp:
    """Runs a command in shell mode, piping in text mode stdout and stderr"""

    def _run(
        command: str, cwd: Path | str | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd or tmp_path_factory.mktemp("shell_run_tmp"),
            text=True,
            check=False,
        )

    return _run
