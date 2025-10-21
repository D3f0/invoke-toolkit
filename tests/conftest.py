from pathlib import Path

import pytest

# from invoke.context import Context
from invoke_toolkit import Context
from typing import Generator


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
    folder = Path(__file__).parent
    return ctx.run(
        f"git -C {folder} rev-parse --show-toplevel",
    ).stdout.strip()


@pytest.fixture
def venv(ctx, tmp_path: Path) -> Generator[Path, None, None]:
    """A virtual environment in a temporary directory"""
    with ctx.cd(tmp_path):
        ctx.run(
            "uv venv",
        )
        yield tmp_path


@pytest.fixture
def package_in_venv(git_root, ctx: Context, venv: Path) -> None:
    """A virtual environment in a temporary directory with the package"""
    ctx.run(f"uv pip install --editable {git_root}")


@pytest.fixture(autouse=True)
def clean_consoles():
    """Resets the console manager"""
    from invoke_toolkit.output.console import manager  # pylint: disable=import-outside-toplevel

    manager._consoles = {}  # pylint: disable=protected-access
