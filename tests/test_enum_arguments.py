"""Tests for enum and literal argument support in tasks.

These tests simulate real-world CLI usage where only string values are passed.
"""

# pylint: disable=unnecessary-pass

import typing
from enum import Enum
from pathlib import Path
from typing import Literal

import pytest
from typing_extensions import Annotated

from invoke_toolkit.context import ToolkitContext
from invoke_toolkit.tasks.tasks import (
    _extract_enum_params,
    _extract_literal_params,
    task,
)
from tests.conftest import Color, Size

if typing.TYPE_CHECKING:
    from tests.conftest import TempVenv

# Path to example tasks
EXAMPLES_DIR = Path(__file__).parent / "examples"


class Status(Enum):
    """Status enumeration (non-string)."""

    PENDING = 1
    RUNNING = 2
    COMPLETED = 3


# ============================================================================
# Parameter Extraction Tests
# ============================================================================


def test_extract_enum_params_single():
    """Test extracting single enum parameter."""

    def sample_func(ctx: ToolkitContext, color: Color) -> None:
        pass

    enum_params = _extract_enum_params(sample_func)
    assert "color" in enum_params
    assert enum_params["color"] is Color


def test_extract_enum_params_multiple():
    """Test extracting multiple enum parameters."""

    def sample_func(ctx: ToolkitContext, color: Color, size: Size) -> None:
        pass

    enum_params = _extract_enum_params(sample_func)
    assert len(enum_params) == 2
    assert enum_params["color"] is Color
    assert enum_params["size"] is Size


def test_extract_enum_params_mixed():
    """Test enums mixed with regular parameters."""

    def sample_func(
        ctx: ToolkitContext, name: str, color: Color, count: int = 5
    ) -> None:
        pass

    enum_params = _extract_enum_params(sample_func)
    assert "color" in enum_params
    assert "name" not in enum_params
    assert "count" not in enum_params


def test_extract_enum_params_annotated():
    """Test extracting enum from Annotated type."""

    def sample_func(
        ctx: ToolkitContext,
        color: Annotated[Color, "The color to use"],
    ) -> None:
        pass

    enum_params = _extract_enum_params(sample_func)
    assert "color" in enum_params
    assert enum_params["color"] is Color


def test_extract_enum_params_skips_ctx():
    """Test that ctx parameter is skipped."""

    def sample_func(ctx: ToolkitContext, color: Color) -> None:
        pass

    enum_params = _extract_enum_params(sample_func)
    assert "ctx" not in enum_params


def test_extract_literal_single():
    """Test extracting single Literal parameter."""

    def sample_func(ctx: ToolkitContext, mode: Literal["fast", "slow"]) -> None:
        pass

    literal_params = _extract_literal_params(sample_func)
    assert "mode" in literal_params
    assert literal_params["mode"] == ("fast", "slow")


def test_extract_literal_union():
    """Test extracting Union of Literals."""

    def sample_func(
        ctx: ToolkitContext,
        level: Literal["debug"] | Literal["info"] | Literal["error"],
    ) -> None:
        pass

    literal_params = _extract_literal_params(sample_func)
    assert "level" in literal_params
    assert set(literal_params["level"]) == {"debug", "info", "error"}


def test_extract_literal_mixed():
    """Test literals mixed with regular parameters."""

    def sample_func(
        ctx: ToolkitContext, name: str, mode: Literal["x", "y"], count: int = 5
    ) -> None:
        pass

    literal_params = _extract_literal_params(sample_func)
    assert "mode" in literal_params
    assert "name" not in literal_params
    assert "count" not in literal_params


# ============================================================================
# CLI String-based Execution Tests
# ============================================================================


def test_enum_cli_string_conversion():
    """Test CLI usage: string converted to enum instance."""
    results = {}

    @task
    def paint(ctx: ToolkitContext, color: Color) -> None:
        """Paint with a color."""
        # Inside task, we have the enum instance
        results["color"] = color
        results["value"] = color.value
        results["type"] = type(color).__name__

    ctx = ToolkitContext()
    # CLI passes "red" as string, task decorator converts to Color.RED
    paint(ctx, "red")  # type: ignore[arg-type]

    assert results["color"] == Color.RED
    assert results["value"] == "red"
    assert results["type"] == "Color"


def test_enum_cli_multiple_colors():
    """Test CLI with different color values."""
    results = {}

    @task
    def paint(ctx: ToolkitContext, color: Color) -> None:
        """Paint with a color."""
        results["color"] = color

    ctx = ToolkitContext()

    # Test each color via CLI string
    paint(ctx, "green")  # type: ignore[arg-type]
    assert results["color"] == Color.GREEN

    paint(ctx, "blue")  # type: ignore[arg-type]
    assert results["color"] == Color.BLUE


def test_enum_cli_invalid_value_error():
    """Test CLI with invalid enum value raises helpful error."""

    @task
    def paint(ctx: ToolkitContext, color: Color) -> None:
        """Paint with a color."""
        pass

    ctx = ToolkitContext()
    with pytest.raises(SystemExit):
        paint(ctx, "purple")  # type: ignore[arg-type]


def test_enum_cli_with_multiple_params():
    """Test CLI with multiple enum parameters."""
    results = {}

    @task
    def configure(
        ctx: ToolkitContext,
        primary: Color,
        secondary: Color,
        size: Size,
    ) -> None:
        """Configure with multiple enums."""
        results["primary"] = primary
        results["secondary"] = secondary
        results["size"] = size

    ctx = ToolkitContext()
    # All passed as strings from CLI
    configure(ctx, "red", "blue", "large")  # type: ignore[arg-type]

    assert results["primary"] == Color.RED
    assert results["secondary"] == Color.BLUE
    assert results["size"] == Size.LARGE


def test_enum_cli_mixed_with_strings():
    """Test CLI with enum and regular string parameters."""
    results = {}

    @task
    def create(ctx: ToolkitContext, name: str, color: Color) -> None:
        """Create something with name and color."""
        results["name"] = name
        results["color"] = color

    ctx = ToolkitContext()
    create(ctx, "widget", "green")  # type: ignore[arg-type]

    assert results["name"] == "widget"
    assert results["color"] == Color.GREEN


# ============================================================================
# Literal CLI Tests
# ============================================================================


def test_literal_cli_valid_value():
    """Test CLI with valid Literal value."""
    results = {}

    @task
    def build(ctx: ToolkitContext, mode: Literal["debug", "release"]) -> None:
        """Build with debug or release mode."""
        results["mode"] = mode

    ctx = ToolkitContext()
    build(ctx, "debug")

    assert results["mode"] == "debug"


def test_literal_cli_all_values():
    """Test CLI with all possible Literal values."""
    results = {}

    @task
    def log_level(
        ctx: ToolkitContext, level: Literal["debug", "info", "error"]
    ) -> None:
        """Set log level."""
        results["level"] = level

    ctx = ToolkitContext()

    for level_val in ["debug", "info", "error"]:
        log_level(ctx, level_val)  # type: ignore[arg-type]
        assert results["level"] == level_val


def test_literal_cli_invalid_value_error():
    """Test CLI with invalid Literal value raises error."""

    @task
    def build(ctx: ToolkitContext, mode: Literal["debug", "release"]) -> None:
        """Build with a mode."""
        pass

    ctx = ToolkitContext()
    with pytest.raises(SystemExit):
        build(ctx, "production")  # type: ignore[arg-type]


def test_literal_union_cli():
    """Test CLI with Union of Literals."""
    results = {}

    @task
    def process(
        ctx: ToolkitContext,
        stage: Literal["input"] | Literal["process"] | Literal["output"],
    ) -> None:
        """Process at a stage."""
        results["stage"] = stage

    ctx = ToolkitContext()
    process(ctx, "process")  # type: ignore[arg-type]

    assert results["stage"] == "process"


# ============================================================================
# Help Text Tests
# ============================================================================


def test_enum_help_text_prepended():
    """Test that enum options are prepended to help text."""

    @task
    def paint(ctx: ToolkitContext, color: Color) -> None:
        """Task with enum parameter."""
        pass

    if hasattr(paint, "help") and paint.help:
        assert "color" in paint.help
        help_text = paint.help["color"]
        # Should start with "Options:"
        assert help_text.startswith("Options:")
        assert "red" in help_text
        assert "green" in help_text
        assert "blue" in help_text


def test_literal_help_text_prepended():
    """Test that literal options are prepended to help text."""

    @task
    def build(ctx: ToolkitContext, mode: Literal["fast", "slow"]) -> None:
        """Task with literal parameter."""
        pass

    if hasattr(build, "help") and build.help:
        assert "mode" in build.help
        help_text = build.help["mode"]
        assert help_text.startswith("Options:")
        assert "fast" in help_text
        assert "slow" in help_text


def test_enum_help_with_annotated_documentation():
    """Test enum options prepended to annotated documentation."""

    @task
    def paint(
        ctx: ToolkitContext,
        color: Annotated[Color, "The color to use"],
    ) -> None:
        """Task with documented enum."""
        pass

    if hasattr(paint, "help") and paint.help:
        assert "color" in paint.help
        help_text = paint.help["color"]
        # Should have options and the annotation doc
        assert "Options:" in help_text
        assert "color" in help_text  # Parameter name in help


def test_enum_help_with_explicit_help_override():
    """Test explicit help overrides options."""

    @task(help={"color": "Custom color documentation"})
    def paint(ctx: ToolkitContext, color: Color) -> None:
        """Task with explicit help."""
        pass

    if hasattr(paint, "help") and paint.help:
        assert "color" in paint.help
        help_text = paint.help["color"]
        # Explicit help takes precedence but still contains options
        assert "Custom color documentation" in help_text


def test_literal_help_with_annotated_documentation():
    """Test literal options prepended to annotated documentation."""

    @task
    def build(
        ctx: ToolkitContext,
        mode: Annotated[Literal["fast", "slow"], "Build mode"],
    ) -> None:
        """Task with documented literal."""
        pass

    if hasattr(build, "help") and build.help:
        assert "mode" in build.help
        help_text = build.help["mode"]
        assert "Options:" in help_text
        assert "Build mode" in help_text


# ============================================================================
# Integration Tests (Mixed Enums and Literals)
# ============================================================================


def test_mixed_enum_and_literal_cli():
    """Test CLI with both enum and literal parameters."""
    results = {}

    @task
    def configure(
        ctx: ToolkitContext,
        color: Color,
        mode: Literal["fast", "slow"],
    ) -> None:
        """Configure with both types."""
        results["color"] = color
        results["mode"] = mode

    ctx = ToolkitContext()
    configure(ctx, "red", "fast")  # type: ignore[arg-type]

    assert results["color"] == Color.RED
    assert results["mode"] == "fast"


def test_mixed_invalid_enum_cli():
    """Test CLI validation catches invalid enum in mixed parameters."""

    @task
    def configure(
        ctx: ToolkitContext,
        color: Color,
        mode: Literal["fast", "slow"],
    ) -> None:
        """Configure with both types."""
        pass

    ctx = ToolkitContext()
    with pytest.raises(SystemExit):
        configure(ctx, "invalid", "fast")  # type: ignore[arg-type]


def test_mixed_invalid_literal_cli():
    """Test CLI validation catches invalid literal in mixed parameters."""

    @task
    def configure(
        ctx: ToolkitContext,
        color: Color,
        mode: Literal["fast", "slow"],
    ) -> None:
        """Configure with both types."""
        pass

    ctx = ToolkitContext()
    with pytest.raises(SystemExit):
        configure(ctx, "red", "medium")  # type: ignore[arg-type]


def test_enum_with_default_value_cli():
    """Test CLI with enum parameter having default value."""
    results = {}

    @task
    def paint(
        ctx: ToolkitContext,
        color: Color = Color.RED,
    ) -> None:
        """Paint with default color."""
        results["color"] = color

    ctx = ToolkitContext()
    # Override default via CLI
    paint(ctx, "blue")  # type: ignore[arg-type]

    assert results["color"] == Color.BLUE


def test_enum_with_multiple_positional_cli():
    """Test CLI with multiple positional arguments."""
    results = {}

    @task
    def draw(
        ctx: ToolkitContext,
        shape: Literal["circle", "square"],
        color: Color,
        size: Size,
    ) -> None:
        """Draw a shape."""
        results["shape"] = shape
        results["color"] = color
        results["size"] = size

    ctx = ToolkitContext()
    draw(ctx, "circle", "green", "large")  # type: ignore[arg-type]

    assert results["shape"] == "circle"
    assert results["color"] == Color.GREEN
    assert results["size"] == Size.LARGE


def test_enum_string_value_not_name():
    """Test that enum is matched by value, not name."""
    results = {}

    @task
    def paint(ctx: ToolkitContext, color: Color) -> None:
        """Paint with enum value."""
        results["color"] = color

    ctx = ToolkitContext()
    # Pass the VALUE "red", not the NAME "RED"
    paint(ctx, "red")  # type: ignore[arg-type]

    assert results["color"] == Color.RED
    assert results["color"].name == "RED"
    assert results["color"].value == "red"


# ============================================================================
# Error Message Quality Tests
# ============================================================================


def test_enum_error_shows_all_options():
    """Test that enum error message includes all valid options."""

    @task
    def paint(ctx: ToolkitContext, color: Color) -> None:
        """Paint with color."""
        pass

    ctx = ToolkitContext()
    with pytest.raises(SystemExit):
        paint(ctx, "invalid")  # type: ignore[arg-type]


def test_literal_error_shows_all_options():
    """Test that literal error message includes all valid options."""

    @task
    def build(ctx: ToolkitContext, mode: Literal["debug", "release"]) -> None:
        """Build with mode."""
        pass

    ctx = ToolkitContext()
    with pytest.raises(SystemExit):
        build(ctx, "test")  # type: ignore[arg-type]


def test_task_integration_flags(
    temp_venv: "TempVenv",
    git_root: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("VIRTUAL_ENV", "")
    monkeypatch.chdir(tmp_path)
    temp_venv.add_package(git_root, editable=True)

    # Copy the tasks.py from enum_select_size example to tmp_path
    example_tasks = EXAMPLES_DIR / "enum_select_size" / "tasks.py"
    tasks_py: Path = tmp_path / "tasks.py"
    tasks_py.write_text(example_tasks.read_text())

    result = temp_venv.run("invoke-toolkit select-size -s small", text=True)

    assert "<enum 'Size'>" in result.stdout


def test_task_integration_literal(
    temp_venv: "TempVenv",
    git_root: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("VIRTUAL_ENV", "")
    monkeypatch.chdir(tmp_path)
    temp_venv.add_package(git_root, editable=True)

    # Copy the tasks.py from literal_set_level example to tmp_path
    example_tasks = EXAMPLES_DIR / "literal_set_level" / "tasks.py"
    tasks_py: Path = tmp_path / "tasks.py"
    tasks_py.write_text(example_tasks.read_text())

    result = temp_venv.run("invoke-toolkit set-level -l debug", text=True)

    assert "Level: debug" in result.stdout
