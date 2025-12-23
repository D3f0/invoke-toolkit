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


def test_auto_print_long_strings_single_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    """Test that long strings remain as a single line when piped to wc -l"""
    ns = ToolkitCollection()
    p = TestingToolkitProgram(
        version="test",
        namespace=ns,
        name="test",
    )

    # Create a string longer than typical terminal width (80+ chars)
    long_string = "B" * 500

    @task(autoprint=True)
    def test_task(ctx: Context):
        """A test function that returns a very long string"""
        return long_string

    ns.add_task(test_task)
    p.run(["", "test-task"])
    output = capsys.readouterr()

    # Count the number of lines in the output
    # When piped to wc -l, a single line without trailing newline would be counted as 0,
    # but with a trailing newline it's 1
    lines = output.out.splitlines()
    assert len(lines) == 1, f"Expected 1 line but got {len(lines)} lines"
    assert lines[0] == long_string
