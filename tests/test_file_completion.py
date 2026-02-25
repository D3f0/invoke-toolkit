"""Tests for file completion with FilePath and FilePattern annotations."""

import io
from contextlib import redirect_stdout
from pathlib import Path

import pytest
from invoke.exceptions import Exit

from invoke_toolkit import (
    Context,
    DirPath,
    FilePath,
    FilePattern,
    DirPathStr,
    FilePathStr,
    FilePatternStr,
    task,
)
from invoke_toolkit.collections import ToolkitCollection
from invoke_toolkit.tasks.types import _FilePathMarker, _FilePatternMarker
from invoke_toolkit.testing import TestingToolkitProgram


def run_completion(coll: ToolkitCollection, task_name: str, flag: str) -> str:
    """
    Run completion for a task and flag, capturing stdout.

    Args:
        coll: The collection containing the task
        task_name: Name of the task to complete
        flag: The flag to complete (e.g., '--path')

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


def test_file_path_type_alias():
    """Test that FilePath() creates correct Annotated type with Path."""
    from typing import Annotated, get_args, get_origin

    from invoke_toolkit.tasks.types import _FileCompletionMarker

    file_path_type = FilePath()
    assert get_origin(file_path_type) is Annotated
    args = get_args(file_path_type)
    assert args[0] is Path
    assert isinstance(args[1], _FileCompletionMarker)


def test_file_pattern_creates_annotated():
    """Test that FilePattern creates correct Annotated type with Path."""
    from typing import Annotated, get_args, get_origin

    from invoke_toolkit.tasks.types import _FileCompletionMarker

    pattern_type = FilePattern("*.py")
    assert get_origin(pattern_type) is Annotated
    args = get_args(pattern_type)
    assert args[0] is Path
    assert isinstance(args[1], _FileCompletionMarker)
    assert args[1].pattern == "*.py"


def test_completion_filepath_lists_files(
    suppress_stderr_logging, tmp_path, monkeypatch
):
    """Test that FilePath() completion lists all files in CWD."""
    # Create test files in tmp_path
    (tmp_path / "file1.txt").touch()
    (tmp_path / "file2.py").touch()
    (tmp_path / "data.json").touch()

    # Change to tmp_path
    monkeypatch.chdir(tmp_path)

    coll = ToolkitCollection()

    @task
    def read(ctx: Context, path: FilePath()) -> None:  # type: ignore[invalid-type-form]
        """Read a file."""

    coll.add_task(read)  # type: ignore[arg-type]

    output = run_completion(coll, "read", "--path")

    assert "file1.txt" in output, f"Expected 'file1.txt' in completion, got: {output}"
    assert "file2.py" in output, f"Expected 'file2.py' in completion, got: {output}"
    assert "data.json" in output, f"Expected 'data.json' in completion, got: {output}"


def test_completion_filepattern_filters_by_glob(
    suppress_stderr_logging, tmp_path, monkeypatch
):
    """Test that FilePattern completion filters files by glob pattern."""
    # Create test files in tmp_path
    (tmp_path / "script.py").touch()
    (tmp_path / "module.py").touch()
    (tmp_path / "data.json").touch()
    (tmp_path / "readme.txt").touch()

    # Change to tmp_path
    monkeypatch.chdir(tmp_path)

    coll = ToolkitCollection()

    @task
    def lint(ctx: Context, file: FilePattern("*.py")) -> None:  # type: ignore[invalid-type-form]
        """Lint Python files."""

    coll.add_task(lint)  # type: ignore[arg-type]

    output = run_completion(coll, "lint", "--file")

    # Should include Python files
    assert "script.py" in output, f"Expected 'script.py' in completion, got: {output}"
    assert "module.py" in output, f"Expected 'module.py' in completion, got: {output}"
    # Should NOT include non-Python files
    assert "data.json" not in output, (
        f"Expected 'data.json' NOT in completion, got: {output}"
    )
    assert "readme.txt" not in output, (
        f"Expected 'readme.txt' NOT in completion, got: {output}"
    )


def test_completion_filepattern_recursive(
    suppress_stderr_logging, tmp_path, monkeypatch
):
    """Test that FilePattern supports recursive glob patterns."""
    # Create directory structure
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (tmp_path / "root.json").touch()
    (subdir / "nested.json").touch()
    (subdir / "other.txt").touch()

    # Change to tmp_path
    monkeypatch.chdir(tmp_path)

    coll = ToolkitCollection()

    @task
    def process(ctx: Context, config: FilePattern("**/*.json")) -> None:  # type: ignore[invalid-type-form]
        """Process JSON config files."""

    coll.add_task(process)  # type: ignore[arg-type]

    output = run_completion(coll, "process", "--config")

    # Should include both root and nested JSON files
    assert "root.json" in output, f"Expected 'root.json' in completion, got: {output}"
    assert "nested.json" in output or "subdir/nested.json" in output, (
        f"Expected nested.json in completion, got: {output}"
    )
    # Should NOT include non-JSON files
    assert "other.txt" not in output, (
        f"Expected 'other.txt' NOT in completion, got: {output}"
    )


def test_file_pattern_invalid_pattern_raises():
    """Test that invalid glob patterns raise ValueError at definition time."""
    # Empty pattern should raise
    with pytest.raises(ValueError, match="cannot be empty"):
        _FilePatternMarker("")


def test_completion_filepath_empty_directory(
    suppress_stderr_logging, tmp_path, monkeypatch
):
    """Test that FilePath() returns empty list for empty directory."""
    # tmp_path is empty by default
    monkeypatch.chdir(tmp_path)

    coll = ToolkitCollection()

    @task
    def read(ctx: Context, path: FilePath()) -> None:  # type: ignore[invalid-type-form]
        """Read a file."""

    coll.add_task(read)  # type: ignore[arg-type]

    output = run_completion(coll, "read", "--path")

    # Should produce empty output (no completions)
    assert output.strip() == "", f"Expected empty output, got: {output}"


def test_file_pattern_does_not_escape_cwd(
    suppress_stderr_logging, tmp_path, monkeypatch
):
    """Test that FilePattern cannot access files outside current directory."""
    # Create a sibling directory with files that should NOT be accessible
    parent = tmp_path.parent
    sibling = parent / "sibling_dir"
    sibling.mkdir(exist_ok=True)
    (sibling / "secret.txt").touch()

    # Create files in tmp_path
    (tmp_path / "local.txt").touch()

    monkeypatch.chdir(tmp_path)

    coll = ToolkitCollection()

    @task
    def process(ctx: Context, file: FilePattern("../**/*.txt")) -> None:  # type: ignore[invalid-type-form]
        """Process text files."""

    coll.add_task(process)  # type: ignore[arg-type]

    output = run_completion(coll, "process", "--file")

    # Should NOT include files from sibling directory
    assert "secret.txt" not in output, (
        f"Security: found file outside cwd in output: {output}"
    )


def test_pathlib_path_auto_detected(suppress_stderr_logging, tmp_path, monkeypatch):
    """Test that pathlib.Path type hint triggers file completion automatically."""
    (tmp_path / "file1.txt").touch()
    (tmp_path / "file2.py").touch()
    monkeypatch.chdir(tmp_path)

    coll = ToolkitCollection()

    @task
    def read(ctx: Context, path: Path) -> None:
        """Read a file using pathlib.Path."""

    coll.add_task(read)  # type: ignore[arg-type]

    output = run_completion(coll, "read", "--path")

    assert "file1.txt" in output, f"Expected 'file1.txt' in completion, got: {output}"
    assert "file2.py" in output, f"Expected 'file2.py' in completion, got: {output}"


def test_optional_path_auto_detected(suppress_stderr_logging, tmp_path, monkeypatch):
    """Test that Optional[Path] / Path | None triggers file completion."""
    (tmp_path / "config.yaml").touch()
    monkeypatch.chdir(tmp_path)

    coll = ToolkitCollection()

    @task
    def load(ctx: Context, config: Path | None = None) -> None:
        """Load optional config."""

    coll.add_task(load)  # type: ignore[arg-type]

    output = run_completion(coll, "load", "--config")

    assert "config.yaml" in output, (
        f"Expected 'config.yaml' in completion, got: {output}"
    )


def test_dirpath_completes_directories_only(
    suppress_stderr_logging, tmp_path, monkeypatch
):
    """Test that DirPath() only completes directories."""
    (tmp_path / "subdir").mkdir()
    (tmp_path / "file.txt").touch()
    monkeypatch.chdir(tmp_path)

    coll = ToolkitCollection()

    @task
    def export(ctx: Context, output_dir: DirPath()) -> None:  # type: ignore[invalid-type-form]
        """Export to directory."""

    coll.add_task(export)  # type: ignore[arg-type]

    output = run_completion(coll, "export", "--output-dir")

    assert "subdir" in output, f"Expected 'subdir' in completion, got: {output}"
    assert "file.txt" not in output, (
        f"Expected 'file.txt' NOT in completion, got: {output}"
    )


def test_filepath_with_dir_okay_false(suppress_stderr_logging, tmp_path, monkeypatch):
    """Test that FilePath(dir_okay=False) only completes files."""
    (tmp_path / "subdir").mkdir()
    (tmp_path / "file.txt").touch()
    monkeypatch.chdir(tmp_path)

    coll = ToolkitCollection()

    @task
    def read(ctx: Context, file: FilePath(dir_okay=False)) -> None:  # type: ignore[invalid-type-form]
        """Read a file only."""

    coll.add_task(read)  # type: ignore[arg-type]

    output = run_completion(coll, "read", "--file")

    assert "file.txt" in output, f"Expected 'file.txt' in completion, got: {output}"
    assert "subdir" not in output, f"Expected 'subdir' NOT in completion, got: {output}"


def test_filepath_subdirectory_traversal(
    suppress_stderr_logging, tmp_path, monkeypatch
):
    """Test that FilePath completes files in subdirectory when user types 'subdir/'."""
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "nested_file.txt").touch()
    (subdir / "another.py").touch()
    (tmp_path / "root.txt").touch()

    monkeypatch.chdir(tmp_path)

    coll = ToolkitCollection()

    @task
    def read(ctx: Context, path: FilePath()) -> None:  # type: ignore[invalid-type-form]
        """Read a file."""

    coll.add_task(read)  # type: ignore[arg-type]

    # Simulate completing with "subdir/" typed
    from invoke_toolkit.completion import _get_file_completions

    marker = _FilePathMarker()
    completions = _get_file_completions(marker, "subdir/")

    assert "subdir/nested_file.txt" in completions, (
        f"Expected 'subdir/nested_file.txt' in completions, got: {completions}"
    )
    assert "subdir/another.py" in completions, (
        f"Expected 'subdir/another.py' in completions, got: {completions}"
    )
    # Should NOT include root files
    assert "root.txt" not in completions, (
        f"Expected 'root.txt' NOT in completions, got: {completions}"
    )


def test_dirpath_subdirectory_traversal(suppress_stderr_logging, tmp_path, monkeypatch):
    """Test that DirPath completes directories in subdirectory."""
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    nested_dir = subdir / "nested-dir"
    nested_dir.mkdir()
    (subdir / "nested_file.txt").touch()  # File should be excluded

    monkeypatch.chdir(tmp_path)

    from invoke_toolkit.completion import _get_file_completions
    from invoke_toolkit.tasks.types import _FileCompletionMarker

    # DirPath uses _FileCompletionMarker with file_okay=False, dir_okay=True
    marker = _FileCompletionMarker(file_okay=False, dir_okay=True)
    completions = _get_file_completions(marker, "subdir/")

    # Should include directories
    assert "subdir/nested-dir" in completions, (
        f"Expected 'subdir/nested-dir' in completions, got: {completions}"
    )
    # Should NOT include files (DirPath excludes files)
    assert "subdir/nested_file.txt" not in completions, (
        f"Expected 'subdir/nested_file.txt' NOT in completions, got: {completions}"
    )


def test_filepath_partial_name_in_subdirectory(
    suppress_stderr_logging, tmp_path, monkeypatch
):
    """Test that partial name like 'subdir/fil' filters by prefix."""
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "file1.txt").touch()
    (subdir / "file2.txt").touch()
    (subdir / "other.txt").touch()

    monkeypatch.chdir(tmp_path)

    from invoke_toolkit.completion import _get_file_completions

    marker = _FilePathMarker()
    completions = _get_file_completions(marker, "subdir/fil")

    # Should include files starting with "fil"
    assert "subdir/file1.txt" in completions, (
        f"Expected 'subdir/file1.txt' in completions, got: {completions}"
    )
    assert "subdir/file2.txt" in completions, (
        f"Expected 'subdir/file2.txt' in completions, got: {completions}"
    )
    # Should NOT include files not starting with "fil"
    assert "subdir/other.txt" not in completions, (
        f"Expected 'subdir/other.txt' NOT in completions, got: {completions}"
    )


def test_subdirectory_traversal_security(
    suppress_stderr_logging, tmp_path, monkeypatch
):
    """Test that '../' cannot traverse outside CWD."""
    # Create sibling directory with sensitive files
    parent = tmp_path.parent
    sibling = parent / "sibling_sensitive"
    sibling.mkdir(exist_ok=True)
    (sibling / "secret.txt").touch()

    # Create our working directory
    (tmp_path / "local.txt").touch()

    monkeypatch.chdir(tmp_path)

    from invoke_toolkit.completion import _get_file_completions

    marker = _FilePathMarker()

    # Try to escape via ../
    completions = _get_file_completions(marker, "../")
    assert completions == [], f"Expected empty list for '../', got: {completions}"

    # Try to escape via ../sibling_sensitive/
    completions = _get_file_completions(marker, "../sibling_sensitive/")
    assert completions == [], (
        f"Expected empty list for '../sibling_sensitive/', got: {completions}"
    )

    # Try to access root
    completions = _get_file_completions(marker, "/")
    assert completions == [], f"Expected empty list for '/', got: {completions}"


def test_path_type_hint_converts_to_path_object():
    """Test that Path type hint converts string argument to pathlib.Path at runtime."""
    received_value = None

    coll = ToolkitCollection()

    @task
    def read_path(ctx: Context, file: Path) -> None:
        nonlocal received_value
        received_value = file

    coll.add_task(read_path)  # type: ignore[arg-type]

    # Simulate invoking the task with a string argument
    read_path.body(None, file="test.txt")  # type: ignore[unresolved-attribute]

    assert isinstance(received_value, Path), (
        f"Expected Path, got {type(received_value)}"
    )
    assert received_value == Path("test.txt")


def test_optional_path_converts_to_path_object():
    """Test that Path | None converts string to pathlib.Path."""
    received_value = None

    coll = ToolkitCollection()

    @task
    def load_config(ctx: Context, config: Path | None = None) -> None:
        nonlocal received_value
        received_value = config

    coll.add_task(load_config)  # type: ignore[arg-type]

    # Test with a value
    load_config.body(None, config="config.yaml")  # type: ignore[unresolved-attribute]
    assert isinstance(received_value, Path), (
        f"Expected Path, got {type(received_value)}"
    )
    assert received_value == Path("config.yaml")

    # Test with None
    load_config.body(None, config=None)  # type: ignore[unresolved-attribute]
    assert received_value is None


def test_path_conversion_with_annotated():
    """Test that Annotated[Path, ...] also converts to pathlib.Path."""
    from typing import Annotated

    received_value = None

    coll = ToolkitCollection()

    @task
    def process(ctx: Context, file: Annotated[Path, "Input file"]) -> None:
        nonlocal received_value
        received_value = file

    coll.add_task(process)  # type: ignore[arg-type]

    process.body(None, file="data.json")  # type: ignore[unresolved-attribute]

    assert isinstance(received_value, Path), (
        f"Expected Path, got {type(received_value)}"
    )
    assert received_value == Path("data.json")


def test_filepath_exists_validation_passes(tmp_path, monkeypatch):
    """Test that FilePath(exists=True) passes for existing files and returns Path."""
    test_file = tmp_path / "exists.txt"
    test_file.write_text("content")
    monkeypatch.chdir(tmp_path)

    result = None

    @task
    def read(ctx: Context, file: FilePath(exists=True)) -> None:  # type: ignore[invalid-type-form]
        nonlocal result
        result = file

    read.body(None, file=str(test_file))  # type: ignore[unresolved-attribute]
    assert isinstance(result, Path), f"Expected Path, got {type(result)}"
    assert result == test_file


def test_filepath_exists_validation_fails(tmp_path, monkeypatch):
    """Test that FilePath(exists=True) raises for non-existent files."""
    monkeypatch.chdir(tmp_path)

    @task
    def read(ctx: Context, file: FilePath(exists=True)) -> None:  # type: ignore[invalid-type-form]
        pass

    with pytest.raises(Exit, match="Path does not exist"):
        read.body(None, file="nonexistent.txt")  # type: ignore[unresolved-attribute]


def test_dirpath_exists_rejects_file(tmp_path, monkeypatch):
    """Test that DirPath(exists=True) rejects files."""
    test_file = tmp_path / "file.txt"
    test_file.write_text("content")
    monkeypatch.chdir(tmp_path)

    @task
    def export(ctx: Context, output_dir: DirPath(exists=True)) -> None:  # type: ignore[invalid-type-form]
        pass

    with pytest.raises(Exit, match="Expected a directory"):
        export.body(None, output_dir=str(test_file))  # type: ignore[unresolved-attribute]


def test_filepath_dir_okay_false_rejects_directory(tmp_path, monkeypatch):
    """Test that FilePath(exists=True, dir_okay=False) rejects directories."""
    test_dir = tmp_path / "subdir"
    test_dir.mkdir()
    monkeypatch.chdir(tmp_path)

    @task
    def read(ctx: Context, file: FilePath(exists=True, dir_okay=False)) -> None:  # type: ignore[invalid-type-form]
        pass

    with pytest.raises(Exit, match="Expected a file"):
        read.body(None, file=str(test_dir))  # type: ignore[unresolved-attribute]


def test_file_path_str_type_alias():
    """Test that FilePathStr() creates correct Annotated type with str."""
    from typing import Annotated, get_args, get_origin

    from invoke_toolkit.tasks.types import _FileCompletionMarker

    file_path_type = FilePathStr()
    assert get_origin(file_path_type) is Annotated
    args = get_args(file_path_type)
    assert args[0] is str
    assert isinstance(args[1], _FileCompletionMarker)


def test_file_pattern_str_creates_annotated():
    """Test that FilePatternStr creates correct Annotated type with str."""
    from typing import Annotated, get_args, get_origin

    from invoke_toolkit.tasks.types import _FileCompletionMarker

    pattern_type = FilePatternStr("*.py")
    assert get_origin(pattern_type) is Annotated
    args = get_args(pattern_type)
    assert args[0] is str
    assert isinstance(args[1], _FileCompletionMarker)
    assert args[1].pattern == "*.py"


def test_dir_path_str_type_alias():
    """Test that DirPathStr() creates correct Annotated type with str."""
    from typing import Annotated, get_args, get_origin

    from invoke_toolkit.tasks.types import _FileCompletionMarker

    dir_path_type = DirPathStr()
    assert get_origin(dir_path_type) is Annotated
    args = get_args(dir_path_type)
    assert args[0] is str
    assert isinstance(args[1], _FileCompletionMarker)
    assert args[1].file_okay is False
    assert args[1].dir_okay is True


def test_dir_path_returns_path_type():
    """Test that DirPath() creates correct Annotated type with Path."""
    from typing import Annotated, get_args, get_origin

    from invoke_toolkit.tasks.types import _FileCompletionMarker

    dir_path_type = DirPath()
    assert get_origin(dir_path_type) is Annotated
    args = get_args(dir_path_type)
    assert args[0] is Path
    assert isinstance(args[1], _FileCompletionMarker)
    assert args[1].file_okay is False
    assert args[1].dir_okay is True
