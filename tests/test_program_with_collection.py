from typing import Any
from invoke_toolkit import task, Context
from invoke_toolkit.collections import ToolkitCollection
from invoke_toolkit.testing import TestingToolkitProgram
import json


@task()
def test_task_1(ctx: Context):
    ctx.run("echo test_task_1")


@task()
def test_task_2(ctx: Context):
    ctx.run("echo test_task_2")


def test_program_with_collection(capsys, suppress_stderr_logging):
    # verify that when the flag -x is passed, the extra collections are also listed
    coll = ToolkitCollection()
    coll.add_task(test_task_1)
    coll.add_task(test_task_2)

    p = TestingToolkitProgram(namespace=coll)
    p.run(["", "-xl", "--list-format", "json"])
    out, err = capsys.readouterr()
    assert not err, f"There should be no err output: {err}"
    task_list: dict[str, Any] = json.loads(out)
    collections = task_list.get("collections")
    assert collections, "collections not found in -x"
    assert set(c["name"] for c in collections).issubset(set(["coll", "config", "dist"]))
