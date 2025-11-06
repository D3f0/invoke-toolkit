from pathlib import Path
import pytest

from invoke_toolkit.context.context import ToolkitContext
from invoke_toolkit.testing import TestingToolkitProgram


def test_new_script(
    capsys: pytest.CaptureFixture,
    tmp_path: Path,
    # task_in_tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    ctx: ToolkitContext,
):
    """
    Runs create.script extension collection
    """
    monkeypatch.chdir(tmp_path)
    x = TestingToolkitProgram()
    x.run(["", "-x", "create.script", "--name", "tasks.py"])
    # out, err = capsys.readouterr()
    current_files = {p.name: p for p in tmp_path.glob("*.py")}
    assert "tasks.py" in current_files
    # script_content = current_files["tasks.py"].read_text()
    script_execution = ctx.run("uv run tasks.py hello-world", warn=True)
    assert script_execution.stdout.strip() == "hello world"


@pytest.mark.skip(reason="Not implemented")
def test_new_package(
    capsys,
    tmp_path,
    # task_in_tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    ctx: ToolkitContext,
):
    monkeypatch.chdir(tmp_path)
    x = TestingToolkitProgram()
    x.run(["", "-x", "coll.init", "--package", "--name", "foo"])
    # out, err = capsys.readouterr()
    # current_files = {p.name: p for p in tmp_path.glob("*.py")}
