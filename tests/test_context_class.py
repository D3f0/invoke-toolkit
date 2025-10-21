from invoke_toolkit import task, Context
from invoke_toolkit.program import InvokeToolkitProgram
from invoke_toolkit.collections import InvokeToolkitCollection


@task()
def task_test(c: Context):
    with c.status("Entering status"):
        c.print("hello")


def test_context_class(capsys):
    @task()
    def task_test(c: Context):
        with c.status("Entering status"):
            c.print("hello")

    p = InvokeToolkitProgram(namespace=InvokeToolkitCollection(task_test))
    p.run(["", "task-test"], exit=False)
    captured = capsys.readouterr()
    # TODO: capture status with custom console object
    out, err = captured.out, captured.err
    assert out.strip() == "hello"
    assert not err.strip()


def test_context_class_pint_err(capsys):
    @task()
    def task_test(c: Context):
        with c.status("Entering status"):
            c.print_err("hello")

    p = InvokeToolkitProgram(namespace=InvokeToolkitCollection(task_test))
    p.run(["", "task-test"], exit=False)
    captured = capsys.readouterr()
    # TODO: capture status with custom console object
    out, err = captured.out, captured.err
    assert not out.strip()
    assert err.strip() == "hello"
