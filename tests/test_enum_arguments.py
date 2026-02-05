"""Tests for enum argument support in tasks."""

from enum import Enum

from invoke_toolkit.context import ToolkitContext
from invoke_toolkit.tasks.tasks import _extract_enum_params, task


class Color(str, Enum):
    """Color enumeration."""

    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class Size(str, Enum):
    """Size enumeration."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class Status(Enum):
    """Status enumeration (non-string)."""

    PENDING = 1
    RUNNING = 2
    COMPLETED = 3


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


def test_extract_enum_params_skips_ctx():
    """Test that ctx parameter is skipped."""

    def sample_func(ctx: ToolkitContext, color: Color) -> None:
        pass

    enum_params = _extract_enum_params(sample_func)
    assert "ctx" not in enum_params


def test_task_with_enum_parameter():
    """Test task decorator with enum parameter."""

    @task
    def my_task(ctx: ToolkitContext, color: Color = Color.RED) -> None:
        """Task with enum parameter."""

    assert my_task is not None


def test_enum_execution_with_instance():
    """Test task execution with enum instance."""
    results = {}

    @task
    def my_task(ctx: ToolkitContext, color: Color) -> None:
        """Task using enum parameter."""
        results["color"] = color
        results["value"] = color.value

    ctx = ToolkitContext()
    my_task(ctx, Color.RED)

    assert results["color"] == Color.RED
    assert results["value"] == "red"


def test_enum_execution_with_string():
    """Test task execution with string converted to enum."""
    results = {}

    @task
    def my_task(ctx: ToolkitContext, color: Color) -> None:
        """Task using enum parameter."""
        results["color"] = color
        results["value"] = color.value

    ctx = ToolkitContext()
    my_task(ctx, "green")  # type: ignore[arg-type]

    assert results["color"] == Color.GREEN
    assert results["value"] == "green"


def test_multiple_enum_parameters():
    """Test task with multiple enum parameters."""
    results = {}

    @task
    def my_task(
        ctx: ToolkitContext,
        primary: Color,
        secondary: Color = Color.RED,
        size: Size = Size.MEDIUM,
    ) -> None:
        """Task with multiple enums."""
        results["primary"] = primary
        results["secondary"] = secondary
        results["size"] = size

    ctx = ToolkitContext()
    my_task(ctx, Color.GREEN, Color.BLUE, Size.LARGE)

    assert results["primary"] == Color.GREEN
    assert results["secondary"] == Color.BLUE
    assert results["size"] == Size.LARGE


def test_enum_with_mixed_params():
    """Test enums mixed with regular parameters."""
    results = {}

    @task
    def my_task(ctx: ToolkitContext, name: str, color: Color, count: int = 5) -> None:
        """Task with mixed parameter types."""
        results["name"] = name
        results["color"] = color
        results["count"] = count

    ctx = ToolkitContext()
    my_task(ctx, "test", Color.RED, 10)

    assert results["name"] == "test"
    assert results["color"] == Color.RED
    assert results["count"] == 10


def test_enum_value_attribute():
    """Test accessing enum value attribute."""

    @task
    def my_task(ctx: ToolkitContext, color: Color) -> None:
        """Task accessing enum value."""
        assert color.value in ("red", "green", "blue")

    ctx = ToolkitContext()
    my_task(ctx, Color.GREEN)


def test_non_string_enum():
    """Test non-string enum support."""
    results = {}

    @task
    def my_task(ctx: ToolkitContext, status: Status) -> None:
        """Task with non-string enum."""
        results["status"] = status
        results["value"] = status.value

    ctx = ToolkitContext()
    my_task(ctx, Status.RUNNING)

    assert results["status"] == Status.RUNNING
    assert results["value"] == 2


def test_enum_help_text():
    """Test that enum help includes choices."""

    @task
    def my_task(ctx: ToolkitContext, color: Color) -> None:
        """Task with enum parameter."""

    if hasattr(my_task, "help") and my_task.help:
        assert "color" in my_task.help
        help_text = my_task.help["color"]
        assert "red" in help_text
        assert "green" in help_text
        assert "blue" in help_text
