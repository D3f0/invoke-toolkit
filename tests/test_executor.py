"""
Tests that the executor uses autoprint
"""

from pathlib import Path

import pytest

# from invoke_toolkit.executor import ToolkitExecutor
from invoke_toolkit import Context, task
from invoke_toolkit.collections import ToolkitCollection
from invoke_toolkit.testing import TestingToolkitProgram


def test_auto_print_uses_rich(tmp_path, monkeypatch, capsys):
    ns = ToolkitCollection()
    p = TestingToolkitProgram(
        version="test",
        namespace=ns,
        name="test",
    )

    expectation = {"a": "1"}

    @task(autoprint=True)
    def test_task(ctx: Context):
        """A test function"""
        return expectation

    ns.add_task(test_task)
    # breakpoint()
    # with pytest.raises(SystemExit):
    p.run(["", "test-task"])
    output = capsys.readouterr()
    assert output.out.strip() == repr(expectation).strip()


def test_auto_print_long_strings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    ns = ToolkitCollection()
    p = TestingToolkitProgram(
        version="test",
        namespace=ns,
        name="test",
    )

    expectation = "A" * 200

    @task(autoprint=True)
    def test_task(ctx: Context):
        """A test function"""
        return expectation

    ns.add_task(test_task)
    # breakpoint()
    # with pytest.raises(SystemExit):
    p.run(["", "test-task"])
    output = capsys.readouterr()
    assert output.out.strip() == expectation
