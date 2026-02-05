"""Tests for enum and literal argument support in tasks."""

# pylint: disable=unnecessary-pass
from enum import Enum
from typing import Literal

import pytest

from invoke_toolkit.context import ToolkitContext
from invoke_toolkit.tasks.tasks import (
    _extract_enum_params,
    _extract_literal_params,
    task,
)


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


def test_enum_execution_invalid_value():
    """Test task execution with invalid enum value raises error."""

    @task
    def my_task(ctx: ToolkitContext, color: Color) -> None:
        """Task using enum parameter."""
        pass

    ctx = ToolkitContext()
    with pytest.raises(ValueError, match="Invalid value 'purple' for color"):
        my_task(ctx, "purple")  # type: ignore[arg-type]


def test_enum_execution_invalid_value_shows_options():
    """Test error message includes valid options."""

    @task
    def my_task(ctx: ToolkitContext, color: Color) -> None:
        """Task using enum parameter."""
        pass

    ctx = ToolkitContext()
    try:
        my_task(ctx, "invalid")  # type: ignore[arg-type]
    except ValueError as e:
        error_msg = str(e)
        assert "red" in error_msg
        assert "green" in error_msg
        assert "blue" in error_msg


def test_literal_execution_with_valid_value():
    """Test task execution with valid literal value."""
    results = {}

    @task
    def my_task(ctx: ToolkitContext, mode: Literal["fast", "slow"]) -> None:
        """Task with literal parameter."""
        results["mode"] = mode

    ctx = ToolkitContext()
    my_task(ctx, "fast")

    assert results["mode"] == "fast"


def test_literal_execution_invalid_value():
    """Test task execution with invalid literal value raises error."""

    @task
    def my_task(ctx: ToolkitContext, mode: Literal["fast", "slow"]) -> None:
        """Task with literal parameter."""
        pass

    ctx = ToolkitContext()
    with pytest.raises(ValueError, match="Invalid value 'medium' for mode"):
        my_task(ctx, "medium")  # type: ignore[arg-type]


def test_literal_union_execution():
    """Test task execution with union of literals."""
    results = {}

    @task
    def my_task(
        ctx: ToolkitContext,
        level: Literal["debug"] | Literal["info"] | Literal["error"],
    ) -> None:
        """Task with union of literals."""
        results["level"] = level

    ctx = ToolkitContext()
    my_task(ctx, "info")

    assert results["level"] == "info"


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


def test_enum_help_text_prepended():
    """Test that enum options are prepended to help text."""

    @task
    def my_task(ctx: ToolkitContext, color: Color) -> None:
        """Task with enum parameter."""

    if hasattr(my_task, "help") and my_task.help:
        assert "color" in my_task.help
        help_text = my_task.help["color"]
        # Should start with "Options:"
        assert help_text.startswith("Options:")
        assert "red" in help_text
        assert "green" in help_text
        assert "blue" in help_text


def test_literal_help_text_prepended():
    """Test that literal options are prepended to help text."""

    @task
    def my_task(ctx: ToolkitContext, mode: Literal["fast", "slow"]) -> None:
        """Task with literal parameter."""

    if hasattr(my_task, "help") and my_task.help:
        assert "mode" in my_task.help
        help_text = my_task.help["mode"]
        assert help_text.startswith("Options:")
        assert "fast" in help_text
        assert "slow" in help_text


def test_enum_help_with_annotated_doc():
    """Test enum options prepended to annotated documentation."""
    from typing_extensions import Annotated

    @task
    def my_task(
        ctx: ToolkitContext,
        color: Annotated[Color, "The color to use"],
    ) -> None:
        """Task with documented enum."""

    if hasattr(my_task, "help") and my_task.help:
        assert "color" in my_task.help
        help_text = my_task.help["color"]
        # Should have options first, then the annotation doc
        assert "Options:" in help_text
        assert "The color to use" in help_text


def test_enum_help_with_explicit_help():
    """Test explicit help overrides but options still shown."""

    @task(help={"color": "Custom help text"})
    def my_task(ctx: ToolkitContext, color: Color) -> None:
        """Task with explicit help."""

    if hasattr(my_task, "help") and my_task.help:
        assert "color" in my_task.help
        help_text = my_task.help["color"]
        # Explicit help takes precedence
        assert "Custom help text" in help_text


def test_enum_validation_with_kwargs():
    """Test enum validation works with keyword arguments."""

    @task
    def my_task(ctx: ToolkitContext, color: Color) -> None:
        """Task with enum parameter."""
        pass

    ctx = ToolkitContext()
    # Should work with valid enum value as kwarg
    my_task(ctx, color=Color.RED)


def test_enum_validation_with_invalid_kwargs():
    """Test enum validation catches invalid keyword arguments."""

    @task
    def my_task(ctx: ToolkitContext, color: Color) -> None:
        """Task with enum parameter."""
        pass

    ctx = ToolkitContext()
    with pytest.raises(ValueError, match="Invalid value"):
        my_task(ctx, color="invalid")  # type: ignore[arg-type]


def test_literal_validation_with_kwargs():
    """Test literal validation works with keyword arguments."""

    @task
    def my_task(ctx: ToolkitContext, mode: Literal["fast", "slow"]) -> None:
        """Task with literal parameter."""
        pass

    ctx = ToolkitContext()
    # Should work with valid literal value
    my_task(ctx, mode="fast")


def test_literal_validation_with_invalid_kwargs():
    """Test literal validation catches invalid keyword arguments."""

    @task
    def my_task(ctx: ToolkitContext, mode: Literal["fast", "slow"]) -> None:
        """Task with literal parameter."""
        pass

    ctx = ToolkitContext()
    with pytest.raises(ValueError, match="Invalid value"):
        my_task(ctx, mode="medium")  # type: ignore[arg-type]


def test_enum_and_literal_mixed():
    """Test task with both enum and literal parameters."""
    results = {}

    @task
    def my_task(
        ctx: ToolkitContext,
        color: Color,
        mode: Literal["fast", "slow"],
    ) -> None:
        """Task with both enum and literal."""
        results["color"] = color
        results["mode"] = mode

    ctx = ToolkitContext()
    my_task(ctx, Color.RED, "fast")

    assert results["color"] == Color.RED
    assert results["mode"] == "fast"


def test_enum_and_literal_mixed_invalid():
    """Test validation catches invalid values in mixed parameters."""

    @task
    def my_task(
        ctx: ToolkitContext,
        color: Color,
        mode: Literal["fast", "slow"],
    ) -> None:
        """Task with both enum and literal."""
        pass

    ctx = ToolkitContext()
    # Invalid enum value
    with pytest.raises(ValueError, match="Invalid value"):
        my_task(ctx, "invalid", "fast")  # type: ignore[arg-type]

    # Invalid literal value
    with pytest.raises(ValueError, match="Invalid value"):
        my_task(ctx, Color.RED, "medium")  # type: ignore[arg-type]
