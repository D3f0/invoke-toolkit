"""
Tests invoke_toolkit.extension.config collection of tasks
"""

import ast
from textwrap import dedent
from invoke_toolkit.program import ToolkitProgram
import pytest


def test_collection(tmp_path, monkeypatch: pytest.MonkeyPatch, capsys):
    tasks = tmp_path / "tasks.py"
    tasks.write_text(
        dedent(
            """
        from invoke_toolkit import task, Context
        
        @task()
        def test(ctx: Context):
            ctx.run("echo hello")
        """
        )
    )
    monkeypatch.chdir(tmp_path)
    p = ToolkitProgram()

    p.run(
        [
            "",
            "-x",
            "config",
        ],
        exit=False,
    )
    caplog = capsys.readouterr()
    out, _err = caplog.out, caplog.err

    assert isinstance(ast.literal_eval(out), dict)
