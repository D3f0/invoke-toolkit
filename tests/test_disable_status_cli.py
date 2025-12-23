"""
Test that the --disable-status CLI flag works correctly.
"""

from typing import cast

import pytest

from invoke_toolkit import task, Context
from invoke_toolkit.testing import TestingToolkitProgram
from invoke_toolkit.collections import ToolkitCollection


@task()
def status_task(ctx: Context):
    """A task that uses the status context manager."""
    with ctx.status("Processing..."):
        ctx.print("hello from status")


def test_disable_status_flag_shows_in_help(capsys, suppress_stderr_logging):
    """Test that --disable-status flag appears in help output."""
    coll = ToolkitCollection(status_task)
    p = TestingToolkitProgram(namespace=coll, binary="test")
    p.run(["", "--help"], exit=False)
    out, _err = capsys.readouterr()

    # The help text should contain the disable-status flag
    assert "--disable-status" in out, f"Expected '--disable-status' in output:\n{out}"
    assert "debugging" in out.lower(), f"Expected 'debugging' in output:\n{out}"


def test_disable_status_flag_disables_status(capsys, suppress_stderr_logging):
    """Test that --disable-status flag disables the status context manager."""
    coll = ToolkitCollection(status_task)
    p = TestingToolkitProgram(namespace=coll, binary="test")

    # Run with --disable-status flag
    p.run(["", "--disable-status", "status-task"], exit=False)
    captured = capsys.readouterr()
    out = captured.out

    # The output should still contain the print output
    assert "hello from status" in out, f"Expected 'hello from status' in output:\n{out}"


def test_status_works_without_disable_flag(capsys, suppress_stderr_logging):
    """Test that status context manager works normally without the flag."""
    coll = ToolkitCollection(status_task)
    p = TestingToolkitProgram(namespace=coll, binary="test")

    # Run without --disable-status flag
    p.run(["", "status-task"], exit=False)
    captured = capsys.readouterr()
    out = captured.out

    # The output should still contain the print output
    assert "hello from status" in out, f"Expected 'hello from status' in output:\n{out}"


def test_disable_status_with_sys_exit(suppress_stderr_logging):
    """Test that --disable-status flag works when task calls sys.exit()"""

    @task()
    def task_with_exit(ctx: Context):
        """A task that exits with a status message."""
        with ctx.status("Preparing..."):
            ctx.print("starting")
        ctx.print("done")
        # Simulate task completion
        import sys

        sys.exit(0)

    coll = ToolkitCollection(task_with_exit)
    p = TestingToolkitProgram(namespace=coll, binary="test")

    # Run with --disable-status flag and task that exits
    # This should raise SystemExit(0)
    with pytest.raises(SystemExit) as exc_info:
        p.run(["", "--disable-status", "task-with-exit"], exit=False)
    assert cast(SystemExit, exc_info.value).code == 0


def test_disable_status_persists_across_calls(capsys, suppress_stderr_logging):
    """Test that disable_status flag persists through multiple status calls in one task"""

    @task()
    def task_multiple_status(ctx: Context):
        """A task with multiple status calls."""
        with ctx.status("First status"):
            ctx.print("message 1")
        with ctx.status("Second status"):
            ctx.print("message 2")
        with ctx.status("Third status"):
            ctx.print("message 3")

    coll = ToolkitCollection(task_multiple_status)
    p = TestingToolkitProgram(namespace=coll, binary="test")

    # Run with --disable-status flag
    p.run(["", "--disable-status", "task-multiple-status"], exit=False)
    captured = capsys.readouterr()
    out = captured.out

    # All messages should appear
    assert "message 1" in out, f"Expected 'message 1' in output:\n{out}"
    assert "message 2" in out, f"Expected 'message 2' in output:\n{out}"
    assert "message 3" in out, f"Expected 'message 3' in output:\n{out}"


def test_disable_status_config_value_set(suppress_stderr_logging):
    """Test that disable_status is properly set in config when flag is used"""

    @task()
    def check_config_task(ctx: Context):
        """A task that checks if disable_status is set in config."""
        # Check that the config has disable_status set to True
        assert ctx.config.get("disable_status", False) is True

    coll = ToolkitCollection(check_config_task)
    p = TestingToolkitProgram(namespace=coll, binary="test")

    # Run with --disable-status flag
    p.run(["", "--disable-status", "check-config-task"], exit=False)
