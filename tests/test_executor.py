"""
Tests that the executor uses autoprint
"""

from invoke_toolkit.collections import ToolkitCollection
from invoke_toolkit.program import ToolkitProgram

# from invoke_toolkit.executor import ToolkitExecutor
from invoke_toolkit import task, Context


def test_auto_print_uses_rich(tmp_path, monkeypatch, capsys):
    ns = ToolkitCollection()
    p = ToolkitProgram(
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
