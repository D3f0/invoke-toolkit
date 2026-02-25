"""Type annotations for task parameters with file completion support."""

from __future__ import annotations

import glob as glob_module
import types
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Union

if TYPE_CHECKING:
    pass


class _FileCompletionMarker:
    """Base marker for file completion with configurable options.

    Provides Click/Typer-style parameters for file path validation and filtering.
    """

    def __init__(
        self,
        *,
        exists: bool = False,
        file_okay: bool = True,
        dir_okay: bool = True,
        pattern: str | None = None,
    ):
        """Initialize file completion marker.

        Args:
            exists: If True, the path must exist (for validation, not completion)
            file_okay: If True, allow files in completion
            dir_okay: If True, allow directories in completion
            pattern: Optional glob pattern to filter files (e.g., "*.py", "**/*.json")
        """
        self.exists = exists
        self.file_okay = file_okay
        self.dir_okay = dir_okay
        self.pattern = pattern

        # Validate pattern if provided
        if pattern is not None:
            if not pattern:
                raise ValueError("File pattern cannot be empty")
            try:
                glob_module.escape(pattern)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid glob pattern '{pattern}': {e}") from e

    def __repr__(self) -> str:
        parts = []
        if self.exists:
            parts.append("exists=True")
        if not self.file_okay:
            parts.append("file_okay=False")
        if not self.dir_okay:
            parts.append("dir_okay=False")
        if self.pattern:
            parts.append(f"pattern={self.pattern!r}")
        return f"_FileCompletionMarker({', '.join(parts)})"


# Legacy markers for backward compatibility
class _FilePathMarker(_FileCompletionMarker):
    """Marker for file path completion - completes all files in current directory."""

    def __init__(self):
        super().__init__()


class _FilePatternMarker(_FileCompletionMarker):
    """Marker for file pattern completion with glob support."""

    def __init__(self, pattern: str = "*"):
        super().__init__(pattern=pattern)


def FilePath(
    *,
    exists: bool = False,
    file_okay: bool = True,
    dir_okay: bool = True,
) -> Any:
    """Create a type annotation for file path completion returning pathlib.Path.

    Similar to Click's Path() type, provides file/directory completion with
    optional validation constraints. The parameter value will be a Path object.

    Usage:
        @task
        def read(ctx: Context, path: FilePath()) -> None:
            '''Complete with any file or directory.'''
            pass

        @task
        def process(ctx: Context, file: FilePath(exists=True, dir_okay=False)) -> None:
            '''Complete with existing files only (no directories).'''
            pass

    Args:
        exists: If True, validates that the path exists at runtime
        file_okay: If True, allow files in completion (default: True)
        dir_okay: If True, allow directories in completion (default: True)

    Returns:
        An Annotated[Path, ...] type that triggers file completion
    """
    return Annotated[
        Path,
        _FileCompletionMarker(
            exists=exists,
            file_okay=file_okay,
            dir_okay=dir_okay,
        ),
    ]


def FilePathStr(
    *,
    exists: bool = False,
    file_okay: bool = True,
    dir_okay: bool = True,
) -> Any:
    """Create a type annotation for file path completion returning str.

    Similar to Click's Path() type, provides file/directory completion with
    optional validation constraints. The parameter value will be a string.

    Usage:
        @task
        def read(ctx: Context, path: FilePathStr()) -> None:
            '''Complete with any file or directory (as string).'''
            pass

        @task
        def process(ctx: Context, file: FilePathStr(exists=True, dir_okay=False)) -> None:
            '''Complete with existing files only (no directories), as string.'''
            pass

    Args:
        exists: If True, validates that the path exists at runtime
        file_okay: If True, allow files in completion (default: True)
        dir_okay: If True, allow directories in completion (default: True)

    Returns:
        An Annotated[str, ...] type that triggers file completion
    """
    return Annotated[
        str,
        _FileCompletionMarker(
            exists=exists,
            file_okay=file_okay,
            dir_okay=dir_okay,
        ),
    ]


def FilePattern(
    pattern: str,
    *,
    exists: bool = False,
) -> Any:
    """Create a type annotation for file completion with a glob pattern returning pathlib.Path.

    Usage:
        @task
        def lint(ctx: Context, file: FilePattern("*.py")) -> None:
            '''Complete with Python files only.'''
            pass

        @task
        def process(ctx: Context, config: FilePattern("**/*.json")) -> None:
            '''Complete with JSON files recursively.'''
            pass

    Args:
        pattern: A glob pattern like "*.py", "**/*.json", "config/*.yaml"
        exists: If True, validates that the path exists at runtime

    Returns:
        An Annotated[Path, ...] type that triggers file completion with the specified pattern

    Raises:
        ValueError: If the glob pattern is invalid or empty
    """
    return Annotated[
        Path,
        _FileCompletionMarker(
            exists=exists,
            file_okay=True,
            dir_okay=False,  # Patterns typically match files
            pattern=pattern,
        ),
    ]


def FilePatternStr(
    pattern: str,
    *,
    exists: bool = False,
) -> Any:
    """Create a type annotation for file completion with a glob pattern returning str.

    Usage:
        @task
        def lint(ctx: Context, file: FilePatternStr("*.py")) -> None:
            '''Complete with Python files only (as string).'''
            pass

        @task
        def process(ctx: Context, config: FilePatternStr("**/*.json")) -> None:
            '''Complete with JSON files recursively (as string).'''
            pass

    Args:
        pattern: A glob pattern like "*.py", "**/*.json", "config/*.yaml"
        exists: If True, validates that the path exists at runtime

    Returns:
        An Annotated[str, ...] type that triggers file completion with the specified pattern

    Raises:
        ValueError: If the glob pattern is invalid or empty
    """
    return Annotated[
        str,
        _FileCompletionMarker(
            exists=exists,
            file_okay=True,
            dir_okay=False,  # Patterns typically match files
            pattern=pattern,
        ),
    ]


def DirPath(
    *,
    exists: bool = False,
) -> Any:
    """Create a type annotation for directory-only completion returning pathlib.Path.

    Convenience wrapper for FilePath(file_okay=False, dir_okay=True).

    Usage:
        @task
        def export(ctx: Context, output_dir: DirPath(exists=True)) -> None:
            '''Complete with existing directories only.'''
            pass

    Args:
        exists: If True, validates that the directory exists at runtime

    Returns:
        An Annotated[Path, ...] type that triggers directory-only completion
    """
    return Annotated[
        Path,
        _FileCompletionMarker(
            exists=exists,
            file_okay=False,
            dir_okay=True,
        ),
    ]


def DirPathStr(
    *,
    exists: bool = False,
) -> Any:
    """Create a type annotation for directory-only completion returning str.

    Convenience wrapper for FilePathStr(file_okay=False, dir_okay=True).

    Usage:
        @task
        def export(ctx: Context, output_dir: DirPathStr(exists=True)) -> None:
            '''Complete with existing directories only (as string).'''
            pass

    Args:
        exists: If True, validates that the directory exists at runtime

    Returns:
        An Annotated[str, ...] type that triggers directory-only completion
    """
    return Annotated[
        str,
        _FileCompletionMarker(
            exists=exists,
            file_okay=False,
            dir_okay=True,
        ),
    ]


# Type for detecting raw pathlib.Path usage
PathTypes = (Path,)


def is_path_type(annotation: Any) -> bool:
    """Check if an annotation is pathlib.Path or a subclass."""
    try:
        # Handle Optional[Path], Path | None, etc.
        from typing import get_args, get_origin

        origin = get_origin(annotation)

        # Handle Union types (including Optional which is Union[X, None])
        # Also handle types.UnionType (Python 3.10+ pipe syntax)
        if origin is Union or isinstance(annotation, types.UnionType):
            args = get_args(annotation)
            # Check if any non-None arg is a Path type
            return any(
                (isinstance(arg, type) and issubclass(arg, Path))
                for arg in args
                if arg is not type(None)
            )

        # Handle Annotated[Path, ...]
        if origin is Annotated:
            args = get_args(annotation)
            if args:
                return is_path_type(args[0])

        # Direct Path type check
        if isinstance(annotation, type):
            return issubclass(annotation, Path)

        return False
    except (TypeError, AttributeError):
        return False
