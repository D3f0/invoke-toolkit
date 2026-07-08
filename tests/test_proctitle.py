"""Tests for proctitle functionality."""

import os
import subprocess
import sys
import time
from pathlib import Path
from textwrap import dedent
from unittest import mock

import pytest
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
    proc = subprocess.Popen(  # pylint: disable=consider-using-with
        [sys.executable, "-m", "invoke_toolkit", "-r", str(tmp_path), "test-proctitle"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        # Wait for the task to signal it's ready
        startup_timeout = 10
        start = time.time()
        while not signal_file.exists():
            if time.time() - start > startup_timeout:
                proc.kill()
                proc.wait(timeout=5)
                pytest.fail("Task did not start in time")
            if proc.poll() is not None:
                stdout, stderr = proc.communicate()
                pytest.fail(
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
        proc.wait(timeout=10)
    finally:
        # Ensure the subprocess is always cleaned up
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)


@pytest.fixture
def mock_tmux_env(monkeypatch):
    """Mock TMUX environment variable."""
    monkeypatch.setenv("TMUX", "/tmp/tmux-1000/default,12345,0")
    return monkeypatch


def test_context_proctitle_calls_tmux_when_in_tmux(mock_tmux_env):
    """Test that ctx.proctitle calls tmux rename-window when $TMUX is set."""
    tmux_calls = []

    def mock_run(args, **kwargs):
        tmux_calls.append(args)
        result = mock.MagicMock()
        result.returncode = 0
        result.stdout = "original-window-name\n"
        return result

    @task()
    def task_with_proctitle(ctx: Context):
        with mock.patch("subprocess.run", side_effect=mock_run):
            with ctx.proctitle("My Task Title"):
                pass

    p = TestingToolkitProgram(namespace=ToolkitCollection(task_with_proctitle))
    p.run(["", "task-with-proctitle"], exit=False)

    # Should have called tmux to get current name, set new name, and restore
    assert any("display-message" in str(call) for call in tmux_calls)
    assert any(
        "rename-window" in str(call) and "My Task Title" in str(call)
        for call in tmux_calls
    )
    assert any(
        "rename-window" in str(call) and "original-window-name" in str(call)
        for call in tmux_calls
    )


def test_task_decorator_proctitle_calls_tmux_when_in_tmux(mock_tmux_env):
    """Test that @task(proctitle=...) calls tmux rename-window when $TMUX is set."""
    tmux_calls = []

    original_run = subprocess.run

    def mock_run(args, check=False, **kwargs):
        if args and "tmux" in str(args[0]):
            tmux_calls.append(args)
            result = mock.MagicMock()
            result.returncode = 0
            result.stdout = "original-window\n"
            return result
        return original_run(args, check=check, **kwargs)

    @task(proctitle="Decorator Task")
    def task_with_decorator(ctx: Context):
        pass

    with mock.patch("subprocess.run", side_effect=mock_run):
        p = TestingToolkitProgram(namespace=ToolkitCollection(task_with_decorator))
        p.run(["", "task-with-decorator"], exit=False)

    # Should have called tmux to get current name, set new name, and restore
    assert any("display-message" in str(call) for call in tmux_calls)
    assert any(
        "rename-window" in str(call) and "Decorator Task" in str(call)
        for call in tmux_calls
    )


def test_proctitle_skips_tmux_when_not_in_tmux(monkeypatch):
    """Test that proctitle does not call tmux when $TMUX is not set."""
    monkeypatch.delenv("TMUX", raising=False)
    tmux_calls = []

    original_run = subprocess.run

    def mock_run(args, check=False, **kwargs):
        if args and "tmux" in str(args[0]):
            tmux_calls.append(args)
        return original_run(args, check=check, **kwargs)

    @task()
    def task_no_tmux(ctx: Context):
        with ctx.proctitle("No Tmux Title"):
            pass

    with mock.patch("subprocess.run", side_effect=mock_run):
        p = TestingToolkitProgram(namespace=ToolkitCollection(task_no_tmux))
        p.run(["", "task-no-tmux"], exit=False)

    # Should not have called tmux at all
    assert len(tmux_calls) == 0


def test_proctitle_restores_tmux_title_on_exception(mock_tmux_env):
    """Test that tmux window title is restored even when exception occurs."""
    tmux_calls = []

    def mock_run(args, **kwargs):
        tmux_calls.append(args)
        result = mock.MagicMock()
        result.returncode = 0
        result.stdout = "original-title\n"
        return result

    @task()
    def task_raises(ctx: Context):
        with mock.patch("subprocess.run", side_effect=mock_run):
            with ctx.proctitle("Before Error"):
                raise ValueError("Test error")

    p = TestingToolkitProgram(namespace=ToolkitCollection(task_raises))
    try:
        p.run(["", "task-raises"], exit=False)
    except ValueError:
        pass

    # Should have restored the original title
    restore_calls = [
        call
        for call in tmux_calls
        if "rename-window" in str(call) and "original-title" in str(call)
    ]
    assert len(restore_calls) >= 1
