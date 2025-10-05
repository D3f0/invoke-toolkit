import pytest
from invoke.context import Context


@pytest.fixture
def ctx() -> Context:
    """
    Returns invoke context
    """
    return Context()


@pytest.fixture
def git_root(ctx) -> str:
    return ctx.run("git rev-parse --show-toplevel", in_stream=False).stdout.strip()
