from dataclasses import dataclass
import os
from pathlib import Path
from textwrap import dedent
from typing import Generator
import pytest
import subprocess
import shlex
from functools import lru_cache
import shutil
from invoke import Context, Config
import unittest.mock
from invoke.program import Program


@pytest.fixture
@lru_cache
def toplevel():
    """Git repository top level"""
    toplevel_ = Path(
        subprocess.check_output("git rev-parse --show-toplevel", shell=True)
        .decode()
        .strip()
    )

    return toplevel_


@pytest.fixture
def package(toplevel, tmp_path: Path):
    """Packages the project in isolated path"""
    files = (
        subprocess.run(
            "git ls-files", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        .stdout.decode()
        .splitlines()
    )
    build = tmp_path / "build"
    build.mkdir(parents=True)
    for file_ in files:
        source = toplevel / file_
        dest = build / file_
        dest.parent.mkdir(exist_ok=True, parents=True)

        shutil.copy(source, dest)

    build_process = subprocess.run(
        shlex.split(f"hatch build -t wheel {tmp_path}"),
        cwd=build,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    exit_code = build_process.returncode
    assert (
        exit_code == 0
    ), f"{build_process.stderr.decode()} {build_process.stdout.decode()}\nExit code: {exit_code}"
    # breakpoint()
    whl, *_more = tmp_path.glob("*.whl")
    assert not _more, f"Dirty whl area, {whl} and {' '.join(_more)} found"
    return whl


@pytest.fixture
def ctx(tmp_path) -> Generator[Context, None, None]:
    """Returns"""
    config = Config()
    config["run"]["in_stream"] = False

    ctx = Context(config=config)
    with ctx.cd(tmp_path):
        yield ctx


@pytest.fixture()
def tmp_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Sets $HOME to tmp_path fixture"""
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_home()


@pytest.fixture()
def tmp_path_in_PATH(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Adds the fixutre tmp_path to $PATH"""
    path = os.getenv("PATH")
    path = f"{tmp_path}:{path}"
    monkeypatch.setenv("PATH", path)


@dataclass
class tasks_py:
    PREAMBLE = dedent(
        """
        from invoke import task, Context

        """
    )
    path: Path

    def __post_init__(self):
        if self.path.is_dir():
            self.path = self.path / "tasks.py"
        self.path.write_text(self.PREAMBLE)

    def add_task(self, name, body="..."):
        current_text = self.path.read_text()
        task_text = dedent(f"""
        @task()
        def {name}(ctx: Context) -> None:
            {body}
        """)
        self.path.write_text("\n".join((current_text, task_text)))


@pytest.fixture()
def task_py_in_tmp_path(tmp_path) -> tasks_py:
    return tasks_py(path=tmp_path)


@pytest.fixture()
def child_timeout() -> int:
    return 3


@pytest.fixture()
def program_no_stdin() -> None:
    """This fixture ensure that the Invoke base program class doesn't try
    to read from the standard input forcing to run the tests without capture"""

    def patched(self: Program):
        config = self.config_class
        config["run"]["in_stream"] = False
        self.config = config

    with unittest.mock.patch("invoke.program.Program.create_config") as mock_config:
        mock_config.side_effect = patched
        yield patched
