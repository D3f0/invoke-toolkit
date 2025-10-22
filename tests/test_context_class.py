from invoke_toolkit import task, Context
from invoke_toolkit.program import ToolkitProgram
from invoke_toolkit.collections import ToolkitCollection


@task()
def task_test(c: Context):
    with c.status("Entering status"):
        c.print("hello")


def test_context_class(capsys):
    @task()
    def task_test(c: Context):
        with c.status("Entering status"):
            c.print("hello")

    p = ToolkitProgram(namespace=ToolkitCollection(task_test))
    p.run(["", "task-test"], exit=False)
    captured = capsys.readouterr()
    # TODO: capture status with custom console object
    out, _err = captured.out, captured.err
    assert out.strip() == "hello"


def test_context_class_pint_err(capsys):
    @task()
    def task_test(c: Context):
        with c.status("Entering status"):
            c.print_err("hello")

    p = ToolkitProgram(namespace=ToolkitCollection(task_test))
    p.run(["", "task-test"], exit=False)
    captured = capsys.readouterr()
    # TODO: capture status with custom console object
    out, err = captured.out, captured.err
    assert not out.strip()
    assert "hello" in err
