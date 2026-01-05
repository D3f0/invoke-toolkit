import json
import subprocess
import sys
from typing import Any

from invoke_toolkit import Context, task
from invoke_toolkit.collections import ToolkitCollection
from invoke_toolkit.testing import TestingToolkitProgram


@task()
def example_task_1(ctx: Context):
    ctx.run("echo example_task_1")


@task()
def example_task_2(ctx: Context):
    ctx.run("echo example_task_2")


def test_program_with_collection(capsys, suppress_stderr_logging):
    # verify that when the flag -x is passed, the extra collections are also listed
    coll = ToolkitCollection()
    coll.add_task(example_task_1)
    coll.add_task(example_task_2)

    p = TestingToolkitProgram(namespace=coll)
    p.run(["", "-xl", "--list-format", "json"])
    out, err = capsys.readouterr()
    assert not err, f"There should be no err output: {err}"
    task_list: dict[str, Any] = json.loads(out)
    collections = task_list.get("collections")
    assert collections, "collections not found in -x"
    assert set(c["name"] for c in collections).issubset(
        set(["create", "config", "dist"])
    )


def test_completion_with_x_flag(suppress_stderr_logging):
    """Test that completion includes internal collections when -x is passed"""
    result = subprocess.run(
        [sys.executable, "-m", "invoke_toolkit", "--complete", "--", "intk", "-x"],
        capture_output=True,
        text=True,
        check=False,
    )

    output = result.stdout + result.stderr

    # Check that internal collections are in the completion output
    assert "config" in output, "config collection should be in completion with -x"
    assert "create" in output, "create collection should be in completion with -x"


def test_completion_without_x_flag(suppress_stderr_logging):
    """Test that completion does not include internal collections without -x"""
    result = subprocess.run(
        [sys.executable, "-m", "invoke_toolkit", "--complete", "--", "intk"],
        capture_output=True,
        text=True,
        check=False,
    )

    output = result.stdout + result.stderr
    lines = output.strip().split("\n")

    # Count how many internal collection items appear
    internal_items = sum(
        1 for line in lines if "config." in line or "create." in line or "dist." in line
    )

    # There should be no internal collection items without -x
    assert internal_items == 0, (
        f"Found {internal_items} internal collection items without -x flag"
    )
