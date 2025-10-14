"""
Tests that the executor uses autoprint
"""

from invoke_toolkit.collections import Collection
from invoke_toolkit.program import InvokeToolkitProgram

# from invoke_toolkit.executor import InvokeToolkitExecutor
from invoke import task, Context


def test_auto_print_uses_rich(tmp_path, monkeypatch, capsys):
    ns = Collection()
    p = InvokeToolkitProgram(
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
    assert output.err.strip() == repr(expectation).strip()
