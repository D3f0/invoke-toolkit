"""Tests for completion with Enum and Literal choices and custom callbacks."""

import io
import os
import tempfile
from contextlib import redirect_stdout
from enum import Enum
from typing import Annotated, Literal

from invoke.exceptions import Exit
from invoke.parser import Argument, ParserContext

from invoke_toolkit import Context, task
from invoke_toolkit.collections import ToolkitCollection
from invoke_toolkit.completion import (
    _get_positional_arg_index,
    _handle_positional_completion,
    get_choices_for_argument,
)
from invoke_toolkit.testing import TestingToolkitProgram
from tests.conftest import Color, Size


def run_completion(coll: ToolkitCollection, task_name: str, flag: str) -> str:
    """
    Run completion for a task and flag, capturing stdout.

    Args:
        coll: The collection containing the task
        task_name: Name of the task to complete
        flag: The flag to complete (e.g., '--branch')

    Returns:
        The completion output as a string
    """
    argv = ["intk", "--complete", "--", "intk", task_name, flag]
    program = TestingToolkitProgram(namespace=coll)
    stdout_capture = io.StringIO()
    with redirect_stdout(stdout_capture):
        try:
            program.run(argv)
        except (SystemExit, Exit):
            pass
    return stdout_capture.getvalue()


def test_completion_enum_choices():
    """Test that completion shows enum choices."""
    coll = ToolkitCollection()

    @task
    def paint(ctx: Context, color: Color = Color.RED) -> None:
        """Paint with a color."""

    coll.add_task(paint)  # type: ignore[arg-type]

    output = run_completion(coll, "paint", "--color")

    assert "red" in output, f"Expected 'red' in completion output, got: {output}"
    assert "green" in output, f"Expected 'green' in completion output, got: {output}"
    assert "blue" in output, f"Expected 'blue' in completion output, got: {output}"


def test_completion_literal_choices():
    """Test that completion shows literal choices."""
    coll = ToolkitCollection()

    @task
    def build(ctx: Context, mode: Literal["debug", "release"] = "debug") -> None:
        """Build with a mode."""

    coll.add_task(build)  # type: ignore[arg-type]

    output = run_completion(coll, "build", "--mode")

    assert "debug" in output, f"Expected 'debug' in completion output, got: {output}"
    assert "release" in output, (
        f"Expected 'release' in completion output, got: {output}"
    )


def test_completion_multiple_enum_params():
    """Test that completion works with multiple enum parameters."""
    coll = ToolkitCollection()

    @task
    def configure(
        ctx: Context,
        color: Color = Color.RED,
        size: Size = Size.MEDIUM,
    ) -> None:
        """Configure with color and size."""

    coll.add_task(configure)  # type: ignore[arg-type]

    # Test color completion
    output = run_completion(coll, "configure", "--color")
    assert "red" in output, f"Expected 'red' in color completion, got: {output}"
    assert "green" in output, f"Expected 'green' in color completion, got: {output}"
    assert "blue" in output, f"Expected 'blue' in color completion, got: {output}"

    # Test size completion
    output = run_completion(coll, "configure", "--size")
    assert "small" in output, f"Expected 'small' in size completion, got: {output}"
    assert "medium" in output, f"Expected 'medium' in size completion, got: {output}"
    assert "large" in output, f"Expected 'large' in size completion, got: {output}"


def test_get_positional_arg_index_no_args():
    """Test _get_positional_arg_index returns 0 when no positional args given."""
    ctx = ParserContext(name="mytask")
    ctx.add_arg(Argument(names=("path",), positional=True))

    tokens = ["mytask"]
    index = _get_positional_arg_index(ctx, tokens)
    assert index == 0


def test_get_positional_arg_index_one_arg():
    """Test _get_positional_arg_index returns 1 when one positional arg given."""
    ctx = ParserContext(name="mytask")
    ctx.add_arg(Argument(names=("path",), positional=True))
    ctx.add_arg(Argument(names=("value",), positional=True))

    tokens = ["mytask", "run.echo"]
    index = _get_positional_arg_index(ctx, tokens)
    assert index == 1


def test_get_positional_arg_index_with_flags():
    """Test _get_positional_arg_index correctly skips flags."""
    ctx = ParserContext(name="mytask")
    ctx.add_arg(Argument(names=("path",), positional=True))
    ctx.add_arg(Argument(names=("format",), default="yaml"))

    tokens = ["mytask", "--format", "json"]
    index = _get_positional_arg_index(ctx, tokens)
    # --format json are flag and value, not positional
    assert index == 0


def test_get_positional_arg_index_no_task_name():
    """Test _get_positional_arg_index returns -1 when no task name in context."""
    ctx = ParserContext()
    tokens = ["something"]
    index = _get_positional_arg_index(ctx, tokens)
    assert index == -1


def test_positional_completion_with_callback():
    """Test positional argument completion uses callback when available."""

    def complete_paths(ctx: Context, incomplete: str) -> list[str]:
        """Return some paths for completion."""
        all_paths = ["run.echo", "run.warn", "tasks.auto_dash_names"]
        if incomplete:
            return [p for p in all_paths if p.startswith(incomplete)]
        return all_paths

    coll = ToolkitCollection()

    @task
    def get_config(
        ctx: Context,
        path: Annotated[str, complete_paths],
    ) -> None:
        """Get a config value."""

    coll.add_task(get_config)  # type: ignore[arg-type]

    # Test getting choices for the positional 'path' argument
    choices = get_choices_for_argument(coll, "get-config", "path", "")
    assert "run.echo" in choices
    assert "run.warn" in choices
    assert "tasks.auto_dash_names" in choices


def test_positional_completion_filters_by_incomplete():
    """Test positional completion filters results by incomplete string."""

    def complete_paths(ctx: Context, incomplete: str) -> list[str]:
        """Return paths filtered by incomplete."""
        all_paths = ["run.echo", "run.warn", "tasks.auto_dash_names"]
        if incomplete:
            return [p for p in all_paths if p.startswith(incomplete)]
        return all_paths

    coll = ToolkitCollection()

    @task
    def get_config(
        ctx: Context,
        path: Annotated[str, complete_paths],
    ) -> None:
        """Get a config value."""

    coll.add_task(get_config)  # type: ignore[arg-type]

    # Test filtering by incomplete
    choices = get_choices_for_argument(coll, "get-config", "path", "run")
    assert "run.echo" in choices
    assert "run.warn" in choices
    assert "tasks.auto_dash_names" not in choices


def test_completion_union_literal():
    """Test that completion works with optional literal parameters (Union with None)."""
    coll = ToolkitCollection()

    @task
    def process(ctx: Context, level: Literal["low", "high"] | None = None) -> None:
        """Process with a level."""

    coll.add_task(process)  # type: ignore[arg-type]

    output = run_completion(coll, "process", "--level")

    assert "low" in output, f"Expected 'low' in union literal completion, got: {output}"
    assert "high" in output, (
        f"Expected 'high' in union literal completion, got: {output}"
    )


def test_completion_callback_basic():
    """Test that completion callbacks are invoked and return choices."""

    def complete_branches(ctx: Context, incomplete: str = "") -> list[str]:
        branches = ["main", "develop", "feature/new-api"]
        return [b for b in branches if b.startswith(incomplete)]

    coll = ToolkitCollection()

    @task
    def deploy(
        ctx: Context,
        branch: Annotated[str, "Git branch to deploy", complete_branches],
    ) -> None:
        pass

    coll.add_task(deploy)  # type: ignore[arg-type]

    output = run_completion(coll, "deploy", "--branch")

    assert "main" in output, f"Expected 'main' in callback completion, got: {output}"
    assert "develop" in output, (
        f"Expected 'develop' in callback completion, got: {output}"
    )
    assert "feature/new-api" in output, (
        f"Expected 'feature/new-api' in callback completion, got: {output}"
    )


def test_completion_callback_with_filtering():
    """Test that completion callbacks filter results based on incomplete value."""

    def complete_branches(ctx: Context, incomplete: str = "") -> list[str]:
        branches = ["main", "develop", "feature/new-api", "feature/another"]
        return [b for b in branches if b.startswith(incomplete)]

    coll = ToolkitCollection()

    @task
    def deploy(
        ctx: Context,
        branch: Annotated[str, "Git branch to deploy", complete_branches],
    ) -> None:
        pass

    coll.add_task(deploy)  # type: ignore[arg-type]

    # Test with no filter - all branches returned via --complete
    output = run_completion(coll, "deploy", "--branch")
    assert "main" in output, f"Expected 'main' in completion, got: {output}"
    assert "develop" in output, f"Expected 'develop' in completion, got: {output}"
    assert "feature/new-api" in output, (
        f"Expected 'feature/new-api' in completion, got: {output}"
    )
    assert "feature/another" in output, (
        f"Expected 'feature/another' in completion, got: {output}"
    )

    # Test filtering via get_choices_for_argument (unit test for callback behavior)
    choices = get_choices_for_argument(coll, "deploy", "branch", incomplete="feature/")
    assert "main" not in choices, f"Unexpected 'main' in filtered completion: {choices}"
    assert "develop" not in choices, (
        f"Unexpected 'develop' in filtered completion: {choices}"
    )
    assert "feature/new-api" in choices, (
        f"Expected 'feature/new-api' in filtered completion, got: {choices}"
    )
    assert "feature/another" in choices, (
        f"Expected 'feature/another' in filtered completion, got: {choices}"
    )

    # Test with "m" filter - only main returned
    choices = get_choices_for_argument(coll, "deploy", "branch", incomplete="m")
    assert choices == ["main"], f"Expected only ['main'], got: {choices}"


def test_completion_callback_priority_over_enum():
    """Test that completion callback has higher priority than enum."""

    class Environment(str, Enum):
        DEV = "dev"
        STAGING = "staging"
        PROD = "prod"

    def complete_env(ctx: Context, incomplete: str = "") -> list[str]:
        # Override enum with dynamic values
        return ["development", "staging", "production"]

    coll = ToolkitCollection()

    @task
    def deploy(
        ctx: Context,
        env: Annotated[Environment, "Deployment environment", complete_env],
    ) -> None:
        pass

    coll.add_task(deploy)  # type: ignore[arg-type]

    output = run_completion(coll, "deploy", "--env")

    # Should use callback results, not enum values
    lines = output.strip().split("\n")
    assert "development" in lines, (
        f"Expected callback result 'development' in completion, got: {lines}"
    )
    assert "staging" in lines, (
        f"Expected callback result 'staging' in completion, got: {lines}"
    )
    assert "production" in lines, (
        f"Expected callback result 'production' in completion, got: {lines}"
    )
    # Ensure enum values are NOT returned (callback takes priority)
    assert "dev" not in lines, f"Unexpected enum value 'dev' in completion: {lines}"
    assert "prod" not in lines, f"Unexpected enum value 'prod' in completion: {lines}"


def test_positional_completion_with_callback_returns_handled_and_suppress():
    """Test that positional completion with callback returns (True, True)."""

    def complete_paths(ctx: Context, incomplete: str) -> list[str]:
        return ["run.echo", "run.warn"]

    coll = ToolkitCollection()

    @task
    def get_value(
        ctx: Context,
        path: Annotated[str, complete_paths],
    ) -> None:
        """Get a value."""

    coll.add_task(get_value)  # type: ignore[arg-type]

    # Create a parser context for the task
    ctx = ParserContext(name="get-value")
    ctx.add_arg(Argument(names=("path",), positional=True))

    # First positional arg (path) - has callback, should return (True, True)
    handled, suppress = _handle_positional_completion(ctx, coll, 0, "")
    assert handled is True, "Should have handled completion with callback"
    assert suppress is True, "Should suppress fallback when handled"


def test_positional_completion_without_callback_returns_not_handled_but_suppress():
    """Test that positional completion without callback returns (False, True)."""
    coll = ToolkitCollection()

    @task
    def set_value(
        ctx: Context,
        path: str,
        value: str,  # No completion callback
    ) -> None:
        """Set a value."""

    coll.add_task(set_value)  # type: ignore[arg-type]

    # Create a parser context for the task
    ctx = ParserContext(name="set-value")
    ctx.add_arg(Argument(names=("path",), positional=True))
    ctx.add_arg(Argument(names=("value",), positional=True))

    # Second positional arg (value) - no callback, should return (False, True)
    # to suppress task name completion
    handled, suppress = _handle_positional_completion(ctx, coll, 1, "")
    assert handled is False, "Should not have handled (no callback)"
    assert suppress is True, (
        "Should suppress fallback for positional arg without callback"
    )


def test_positional_completion_out_of_range_allows_task_completion():
    """Test that completion after all positional args allows task names."""
    coll = ToolkitCollection()

    @task
    def simple_task(
        ctx: Context,
        name: str,
    ) -> None:
        """A simple task."""

    coll.add_task(simple_task)  # type: ignore[arg-type]

    # Create a parser context for the task
    ctx = ParserContext(name="simple-task")
    ctx.add_arg(Argument(names=("name",), positional=True))

    # Index 1 is out of range (only 1 positional arg at index 0)
    # Should return (False, False) to allow task name completion
    handled, suppress = _handle_positional_completion(ctx, coll, 1, "")
    assert handled is False, "Should not have handled (out of range)"
    assert suppress is False, "Should NOT suppress fallback when out of range"


def test_completion_without_task_file_with_internal_col_flag():
    """Test that completion works without task file when -x flag is in completion context.

    This tests GitHub issue #57: When using tab completion without a task file,
    completion of -x extensions should not trigger task discovery errors.
    """
    # Create a temporary directory without any task files
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Simulate completion with -x flag in completion context
            # Shell calls: intk --complete -- intk -x config
            argv = ["intk", "--complete", "--", "intk", "-x", "config"]
            program = TestingToolkitProgram()
            stdout_capture = io.StringIO()

            with redirect_stdout(stdout_capture):
                try:
                    program.run(argv)
                except (SystemExit, Exit):
                    pass

            output = stdout_capture.getvalue()

            # Should show internal collection tasks, not an error
            assert "config" in output, (
                f"Expected 'config' in completion output, got: {output}"
            )
            # Should NOT contain the error message
            assert "Can't find any collection" not in output, (
                f"Should not show error message, got: {output}"
            )
        finally:
            os.chdir(original_cwd)


def test_completion_with_search_root_flag():
    """Test that completion works with -r/--search-root flag.

    This tests GitHub issue #54: When using tab completion with -r <path>,
    the completions should show tasks from the specified directory, not
    the current working directory.
    """
    # Create a temporary directory with a tasks.py file
    with tempfile.TemporaryDirectory() as tmpdir:
        tasks_file = os.path.join(tmpdir, "tasks.py")
        with open(tasks_file, "w", encoding="utf-8") as f:
            f.write(
                "from invoke_toolkit import task, Context\n"
                "@task\n"
                "def custom_task_one(ctx):\n"
                "    pass\n"
                "@task\n"
                "def custom_task_two(ctx):\n"
                "    pass\n"
            )

        # Test with -r short flag
        argv = ["intk", "--complete", "--", "intk", "-r", tmpdir, ""]
        program = TestingToolkitProgram()
        stdout_capture = io.StringIO()

        with redirect_stdout(stdout_capture):
            try:
                program.run(argv)
            except (SystemExit, Exit):
                pass

        output = stdout_capture.getvalue()

        # Should show tasks from the temp directory
        assert "custom-task-one" in output, (
            f"Expected 'custom-task-one' in completion output, got: {output}"
        )
        assert "custom-task-two" in output, (
            f"Expected 'custom-task-two' in completion output, got: {output}"
        )


def test_completion_with_search_root_long_flag():
    """Test that completion works with --search-root long flag."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tasks_file = os.path.join(tmpdir, "tasks.py")
        with open(tasks_file, "w", encoding="utf-8") as f:
            f.write(
                "from invoke_toolkit import task, Context\n"
                "@task\n"
                "def my_custom_task(ctx):\n"
                "    pass\n"
            )

        # Test with --search-root long flag
        argv = ["intk", "--complete", "--", "intk", "--search-root", tmpdir, ""]
        program = TestingToolkitProgram()
        stdout_capture = io.StringIO()

        with redirect_stdout(stdout_capture):
            try:
                program.run(argv)
            except (SystemExit, Exit):
                pass

        output = stdout_capture.getvalue()

        assert "my-custom-task" in output, (
            f"Expected 'my-custom-task' in completion output, got: {output}"
        )


def test_completion_search_root_shows_directories():
    """Test that -r/--search-root flag completes with directory names.

    This tests GitHub issue #54: The -r flag should complete with directories
    so users can easily navigate to the location of their tasks.py file.
    """
    # Simulating completion: intk -r <TAB>
    argv = ["intk", "--complete", "--", "intk", "-r", ""]
    program = TestingToolkitProgram()
    stdout_capture = io.StringIO()

    with redirect_stdout(stdout_capture):
        try:
            program.run(argv)
        except (SystemExit, Exit):
            pass

    output = stdout_capture.getvalue()
    lines = output.strip().split("\n")

    # Should show directories, not task names
    # The test directory should contain at least 'src', 'tests', 'docs' directories
    assert any("src" in line or "tests" in line for line in lines), (
        f"Expected directory names in completion output, got: {lines}"
    )

    # Should NOT show task names (like 'build', 'test', etc.)
    # Task names typically don't look like directory names
    assert "build" not in lines, (
        f"Should not show task names in -r completion, got: {lines}"
    )


def test_completion_search_root_filters_by_prefix():
    """Test that -r completion filters directories by prefix."""
    # Simulating completion: intk -r tes<TAB>
    argv = ["intk", "--complete", "--", "intk", "-r", "tes"]
    program = TestingToolkitProgram()
    stdout_capture = io.StringIO()

    with redirect_stdout(stdout_capture):
        try:
            program.run(argv)
        except (SystemExit, Exit):
            pass

    output = stdout_capture.getvalue()
    lines = [line for line in output.strip().split("\n") if line]

    # Should only show directories starting with 'tes'
    for line in lines:
        assert line.startswith("tes"), (
            f"Expected all completions to start with 'tes', got: {line}"
        )


def test_completion_search_root_subdirectory():
    """Test that -r completion works for subdirectories."""
    # Simulating completion: intk -r src/<TAB>
    argv = ["intk", "--complete", "--", "intk", "-r", "src/"]
    program = TestingToolkitProgram()
    stdout_capture = io.StringIO()

    with redirect_stdout(stdout_capture):
        try:
            program.run(argv)
        except (SystemExit, Exit):
            pass

    output = stdout_capture.getvalue()
    lines = [line for line in output.strip().split("\n") if line]

    # Should show subdirectories of src/
    assert any("src/invoke_toolkit" in line for line in lines), (
        f"Expected 'src/invoke_toolkit' in completion output, got: {lines}"
    )


def test_completion_flags_without_tasks_file():
    """Test that flag completion works even when no tasks.py exists.

    This tests GitHub issue #54: When there's no tasks.py file, users should
    still be able to complete core flags like -r, -x, --help, etc.
    """
    # Create a temporary directory without any task files
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Simulating completion: intk -<TAB>
            argv = ["intk", "--complete", "--", "intk", "-"]
            program = TestingToolkitProgram()
            stdout_capture = io.StringIO()

            with redirect_stdout(stdout_capture):
                try:
                    program.run(argv)
                except (SystemExit, Exit):
                    pass

            output = stdout_capture.getvalue()
            lines = [line for line in output.strip().split("\n") if line]

            # Should show core flags, not an error
            assert len(lines) > 0, "Expected flag completions, got empty output"

            # Should include common flags
            assert any("--help" in line or "-h" in line for line in lines), (
                f"Expected --help in completion output, got: {lines}"
            )
            assert any("--search-root" in line or "-r" in line for line in lines), (
                f"Expected --search-root/-r in completion output, got: {lines}"
            )

            # Should NOT contain the error message
            assert not any("Can't find any collection" in line for line in lines), (
                f"Should not show error message, got: {lines}"
            )
        finally:
            os.chdir(original_cwd)


def test_completion_search_root_without_tasks_file():
    """Test that -r directory completion works even when no tasks.py exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            # Create some subdirectories
            os.makedirs("project1")
            os.makedirs("project2")

            # Simulating completion: intk -r <TAB>
            argv = ["intk", "--complete", "--", "intk", "-r", ""]
            program = TestingToolkitProgram()
            stdout_capture = io.StringIO()

            with redirect_stdout(stdout_capture):
                try:
                    program.run(argv)
                except (SystemExit, Exit):
                    pass

            output = stdout_capture.getvalue()
            lines = [line for line in output.strip().split("\n") if line]

            # Should show the directories we created
            assert "project1" in lines, (
                f"Expected 'project1' in completion output, got: {lines}"
            )
            assert "project2" in lines, (
                f"Expected 'project2' in completion output, got: {lines}"
            )
        finally:
            os.chdir(original_cwd)
