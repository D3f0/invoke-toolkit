import pytest

from invoke_toolkit.testing import TestingToolkitProgram


def test_new_script(
    capsys,
    tmp_path,
    # task_in_tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    ctx,
):
    monkeypatch.chdir(tmp_path)
    x = TestingToolkitProgram()
    x.run(["", "-x", "coll.init"])
    # out, err = capsys.readouterr()
    current_files = {p.name: p for p in tmp_path.glob("*.py")}
    assert "tasks.py" in current_files
    # script_content = current_files["tasks.py"].read_text()
    script_execution = ctx.run("uv run tasks.py hello-world", warn=True)
    assert script_execution.stdout.strip() == "hello world"
