"""Tests for proctitle functionality."""

import os
import subprocess
import sys
import time
from pathlib import Path
from textwrap import dedent

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


def test_proctitle_visible_in_ps(tmp_path: Path):
    """Integration test: verify process title is visible via ps command."""
    # Create a tasks.py with a task that sets proctitle and waits for a signal
    unique_title = f"INTK_TEST_PROCTITLE_{os.getpid()}"
    signal_file = tmp_path / "ready"
    done_file = tmp_path / "done"

    tasks_content = dedent(f"""
        import time
        from pathlib import Path
        from invoke_toolkit import task, Context

        @task(proctitle="{unique_title}")
        def test_proctitle(ctx: Context):
            # Signal that we're running
            Path("{signal_file}").write_text("ready")
            # Wait for done signal
            while not Path("{done_file}").exists():
                time.sleep(0.05)
    """)

    tasks_file = tmp_path / "tasks.py"
    tasks_file.write_text(tasks_content)

    # Start the task in a subprocess
    with subprocess.Popen(
        [sys.executable, "-m", "invoke_toolkit", "-r", str(tmp_path), "test-proctitle"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        # Wait for the task to signal it's ready
        timeout = 10
        start = time.time()
        while not signal_file.exists():
            if time.time() - start > timeout:
                raise TimeoutError("Task did not start in time")
            if proc.poll() is not None:
                stdout, stderr = proc.communicate()
                raise RuntimeError(
                    f"Process exited early: {proc.returncode}\n"
                    f"stdout: {stdout.decode()}\nstderr: {stderr.decode()}"
                )
            time.sleep(0.05)

        # Check the process title using ps
        ps_result = subprocess.run(
            ["ps", "-p", str(proc.pid), "-o", "command="],
            capture_output=True,
            text=True,
            check=False,
        )

        # Verify the unique title appears in ps output
        assert unique_title in ps_result.stdout, (
            f"Expected '{unique_title}' in ps output, got: {ps_result.stdout}"
        )

        # Signal the task to finish
        done_file.write_text("done")
        proc.wait(timeout=5)
