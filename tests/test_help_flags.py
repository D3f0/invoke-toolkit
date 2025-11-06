"""
Test that boolean flag help text is rendered correctly with --[no-]flag syntax.
"""

from invoke import Context
from invoke_toolkit.tasks import task
from invoke_toolkit.collections import ToolkitCollection
from invoke_toolkit.testing import TestingToolkitProgram


@task()
def bool_flag_task(ctx: Context, enable=True):
    """A task with a boolean flag that defaults to True."""


@task()
def bool_flag_disabled(ctx: Context, disable=False):
    """A task with a boolean flag that defaults to False."""


def test_bool_flag_help_text_default_true(capsys, suppress_stderr_logging):
    """Test that boolean flags with default=True show --[no-]flag syntax."""
    coll = ToolkitCollection()
    coll.add_task(bool_flag_task)

    p = TestingToolkitProgram(namespace=coll, binary="test")
    p.run(["", "bool-flag-task", "-h"])
    out, _err = capsys.readouterr()

    # The help text should contain the --[no-]flag syntax
    assert "--[no-]enable" in out, f"Expected '--[no-]enable' in output:\n{out}"


def test_bool_flag_help_text_default_false(capsys, suppress_stderr_logging):
    """Test that boolean flags with default=False show simple --flag syntax."""
    coll = ToolkitCollection()
    coll.add_task(bool_flag_disabled)

    p = TestingToolkitProgram(namespace=coll, binary="test")
    p.run(["", "bool-flag-disabled", "-h"])
    out, _err = capsys.readouterr()

    # The help text should not show the inverse flag for default=False
    assert "--disable" in out, f"Expected '--disable' in output:\n{out}"
    # Should not have the [no-] syntax for default False flags
    assert "--[no-]disable" not in out, f"Unexpected '--[no-]disable' in output:\n{out}"
