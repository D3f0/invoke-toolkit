import json
import logging
import os
import subprocess
import sys
from enum import Enum
from pathlib import Path
from textwrap import dedent
from typing import Any, Protocol

import attrs
import pytest
from tomlkit import TOMLDocument, dump, parse

# from invoke.context import Context
from invoke_toolkit import Context
from invoke_toolkit.output.console import manager


class Color(str, Enum):
    """Color enumeration for testing."""

    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class Size(str, Enum):
    """Size enumeration for testing."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


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


def add_entrypoint(pth: str | Path, name: str, value: Any) -> None:
    """Adds an entry-point to a pyproject.toml file defined by pth"""
    if isinstance(pth, (str, Path)):
        with open(pth, encoding="utf-8") as fp:
            toml: TOMLDocument = parse(fp.read())
    else:
        raise ValueError(pth)
    entry_points = toml["project"].setdefault("entry-points", {})  # type: ignore[union-attr]
    entry_points[name] = value
    with open(pth, mode="w", encoding="utf-8") as fp:
        dump(toml, fp)


@pytest.fixture(autouse=True)
def clean_consoles():
    """Resets the console manager"""
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
        self,
        command: str,
        cwd: Path | None = None,
        text: bool = False,
    ) -> subprocess.CompletedProcess[bytes] | subprocess.CompletedProcess[str]:
        """Internal call to the process"""
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            env=self._uv_venv,
            cwd=cwd,
            check=False,
            text=text,
        )
        # assert result.returncode == 0
        return result

    def run(
        self,
        command: str,
        cwd: Path | None = None,
        text: bool = False,
    ) -> subprocess.CompletedProcess[bytes] | subprocess.CompletedProcess[str]:
        """Runs a command in the virtual environment"""
        return self._call(f"uv run {command}", cwd=cwd, text=text)

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
        capture_output=True,
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
            capture_output=True,
            cwd=cwd or tmp_path_factory.mktemp("shell_run_tmp"),
            text=True,
            check=False,
        )

    return _run
