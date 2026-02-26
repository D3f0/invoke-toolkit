"""Tests for proctitle functionality."""

import setproctitle

from invoke_toolkit import Context, task
from invoke_toolkit.collections import ToolkitCollection
from invoke_toolkit.testing import TestingToolkitProgram


def test_context_proctitle_context_manager():
    """Test that ctx.proctitle context manager sets and restores process title."""
    original_title = setproctitle.getproctitle()
    titles_during_execution = []

    @task()
    def task_with_proctitle(ctx: Context):
        titles_during_execution.append(setproctitle.getproctitle())
        with ctx.proctitle("Test Process Title"):
            titles_during_execution.append(setproctitle.getproctitle())
        titles_during_execution.append(setproctitle.getproctitle())

    p = TestingToolkitProgram(namespace=ToolkitCollection(task_with_proctitle))
    p.run(["", "task-with-proctitle"], exit=False)

    assert titles_during_execution[0] == original_title
    assert titles_during_execution[1] == "Test Process Title"
    assert titles_during_execution[2] == original_title


def test_context_proctitle_restores_on_exception():
    """Test that ctx.proctitle restores title even when exception occurs."""
    original_title = setproctitle.getproctitle()

    @task()
    def task_with_exception(ctx: Context):
        with ctx.proctitle("Before Exception"):
            raise ValueError("Test exception")

    p = TestingToolkitProgram(namespace=ToolkitCollection(task_with_exception))
    try:
        p.run(["", "task-with-exception"], exit=False)
    except ValueError:
        pass

    assert setproctitle.getproctitle() == original_title


def test_task_decorator_proctitle():
    """Test that @task(proctitle=...) sets process title during task execution."""
    original_title = setproctitle.getproctitle()
    title_during_execution = []

    @task(proctitle="Decorator Process Title")
    def task_with_decorator_proctitle(ctx: Context):
        title_during_execution.append(setproctitle.getproctitle())

    p = TestingToolkitProgram(
        namespace=ToolkitCollection(task_with_decorator_proctitle)
    )
    p.run(["", "task-with-decorator-proctitle"], exit=False)

    assert title_during_execution[0] == "Decorator Process Title"
    assert setproctitle.getproctitle() == original_title


def test_task_decorator_proctitle_restores_on_exception():
    """Test that @task(proctitle=...) restores title even on exception."""
    original_title = setproctitle.getproctitle()

    @task(proctitle="Before Exception")
    def task_raises(ctx: Context):
        raise ValueError("Test exception")

    p = TestingToolkitProgram(namespace=ToolkitCollection(task_raises))
    try:
        p.run(["", "task-raises"], exit=False)
    except ValueError:
        pass

    assert setproctitle.getproctitle() == original_title


def test_nested_proctitle_context_managers():
    """Test nested ctx.proctitle context managers restore properly."""
    original_title = setproctitle.getproctitle()
    titles = []

    @task()
    def task_nested(ctx: Context):
        titles.append(setproctitle.getproctitle())
        with ctx.proctitle("Level 1"):
            titles.append(setproctitle.getproctitle())
            with ctx.proctitle("Level 2"):
                titles.append(setproctitle.getproctitle())
            titles.append(setproctitle.getproctitle())
        titles.append(setproctitle.getproctitle())

    p = TestingToolkitProgram(namespace=ToolkitCollection(task_nested))
    p.run(["", "task-nested"], exit=False)

    assert titles[0] == original_title
    assert titles[1] == "Level 1"
    assert titles[2] == "Level 2"
    assert titles[3] == "Level 1"
    assert titles[4] == original_title


def test_decorator_and_context_manager_combined():
    """Test combining @task(proctitle=...) with ctx.proctitle()."""
    original_title = setproctitle.getproctitle()
    titles = []

    @task(proctitle="Task Level")
    def task_combined(ctx: Context):
        titles.append(setproctitle.getproctitle())
        with ctx.proctitle("Inner Level"):
            titles.append(setproctitle.getproctitle())
        titles.append(setproctitle.getproctitle())

    p = TestingToolkitProgram(namespace=ToolkitCollection(task_combined))
    p.run(["", "task-combined"], exit=False)

    assert titles[0] == "Task Level"
    assert titles[1] == "Inner Level"
    assert titles[2] == "Task Level"
    assert setproctitle.getproctitle() == original_title


def test_task_without_proctitle():
    """Test that tasks without proctitle don't change the process title."""
    original_title = setproctitle.getproctitle()
    title_during_execution = []

    @task()
    def regular_task(ctx: Context):
        title_during_execution.append(setproctitle.getproctitle())

    p = TestingToolkitProgram(namespace=ToolkitCollection(regular_task))
    p.run(["", "regular-task"], exit=False)

    assert title_during_execution[0] == original_title
    assert setproctitle.getproctitle() == original_title
