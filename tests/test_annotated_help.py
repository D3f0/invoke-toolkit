"""Tests for Annotated help extraction and task decorator integration."""

from typing import Any

from typing_extensions import Annotated

from invoke_toolkit.context import ToolkitContext
from invoke_toolkit.tasks.tasks import _extract_annotated_help, task


def test_extract_annotated_help_single_param():
    """Test extracting help from a single Annotated parameter."""

    def sample_func(
        name: Annotated[str, "The target name"],
    ) -> None:
        pass

    help_dict = _extract_annotated_help(sample_func)
    assert help_dict == {"name": "The target name"}


def test_extract_annotated_help_multiple_params():
    """Test extracting help from multiple Annotated parameters."""

    def sample_func(
        name: Annotated[str, "The target name"],
        count: Annotated[int, "Number of iterations"],
        verbose: Annotated[bool, "Enable verbose output"],
    ) -> None:
        pass

    help_dict = _extract_annotated_help(sample_func)
    assert help_dict == {
        "name": "The target name",
        "count": "Number of iterations",
        "verbose": "Enable verbose output",
    }


def test_extract_annotated_help_skips_ctx():
    """Test that ctx parameter is skipped in help extraction."""

    def sample_func(
        ctx: Annotated[ToolkitContext, "The context"],
        name: Annotated[str, "The target name"],
    ) -> None:
        pass

    help_dict = _extract_annotated_help(sample_func)
    assert "ctx" not in help_dict
    assert help_dict == {"name": "The target name"}


def test_extract_annotated_help_skips_c():
    """Test that c parameter (alternate for ctx) is skipped."""

    def sample_func(
        c: Annotated[Any, "The context"],
        name: Annotated[str, "The target name"],
    ) -> None:
        pass

    help_dict = _extract_annotated_help(sample_func)
    assert "c" not in help_dict
    assert help_dict == {"name": "The target name"}


def test_extract_annotated_help_skips_underscore_params():
    """Test that parameters starting with underscore are skipped."""

    def sample_func(
        name: Annotated[str, "The target name"],
        _private: Annotated[str, "This should be skipped"],
    ) -> None:
        pass

    help_dict = _extract_annotated_help(sample_func)
    assert "_private" not in help_dict
    assert help_dict == {"name": "The target name"}


def test_extract_annotated_help_mixed_params():
    """Test extracting help with mix of Annotated and non-Annotated params."""

    def sample_func(
        name: Annotated[str, "The target name"],
        count: int = 5,  # No annotation help
        verbose: Annotated[bool, "Enable verbose output"] = False,
    ) -> None:
        pass

    help_dict = _extract_annotated_help(sample_func)
    assert help_dict == {
        "name": "The target name",
        "verbose": "Enable verbose output",
    }
    assert "count" not in help_dict


def test_extract_annotated_help_no_annotated():
    """Test extracting help from function with no Annotated params."""

    def sample_func(
        name: str,
        count: int = 5,
    ) -> None:
        pass

    help_dict = _extract_annotated_help(sample_func)
    assert not help_dict


def test_extract_annotated_help_empty_function():
    """Test extracting help from function with only ctx param."""

    def sample_func(ctx: ToolkitContext) -> None:
        pass

    help_dict = _extract_annotated_help(sample_func)
    assert not help_dict


def test_task_decorator_merges_annotated_help():
    """Test that @task decorator automatically merges Annotated help."""

    @task
    def my_task(
        ctx: ToolkitContext,
        name: Annotated[str, "The target name"],
        count: Annotated[int, "Number of iterations"] = 5,
    ) -> None: ...

    # The task's help should contain the Annotated documentation
    assert hasattr(my_task, "help")
    assert my_task.help is not None  # type: ignore[attr-defined]
    assert my_task.help["name"] == "The target name"  # type: ignore[attr-defined]
    assert my_task.help["count"] == "Number of iterations"  # type: ignore[attr-defined]


def test_task_decorator_explicit_help_overrides():
    """Test that explicit help dict takes precedence over Annotated."""

    @task(help={"name": "Override annotation doc"})
    def my_task(
        ctx: ToolkitContext,
        name: Annotated[str, "Original annotation doc"],
        count: Annotated[int, "Number of iterations"] = 5,
    ) -> None: ...

    # The explicit help should override the Annotated help
    assert my_task.help["name"] == "Override annotation doc"  # type: ignore[attr-defined]
    # But other Annotated help should still be present
    assert my_task.help["count"] == "Number of iterations"  # type: ignore[attr-defined]


def test_task_decorator_mixed_help():
    """Test task with both Annotated and explicit help entries."""

    @task(help={"extra": "An extra parameter doc"})
    def my_task(
        ctx: ToolkitContext,
        name: Annotated[str, "The target name"],
        extra: Annotated[str, "Will be overridden"] = "",
    ) -> None: ...

    # Both Annotated and explicit help should be present
    assert my_task.help["name"] == "The target name"  # type: ignore[attr-defined]
    # Explicit help takes precedence
    assert my_task.help["extra"] == "An extra parameter doc"  # type: ignore[attr-defined]


def test_extract_annotated_help_non_string_annotation():
    """Test that non-string annotations in Annotated are skipped."""

    def sample_func(
        name: Annotated[str, "The target name"],
        # This has a non-string annotation metadata, should be skipped
        count: Annotated[int, 123],
    ) -> None:
        pass

    help_dict = _extract_annotated_help(sample_func)
    assert help_dict == {"name": "The target name"}
    assert "count" not in help_dict


def test_task_decorator_no_help_needed():
    """Test task decorator with no explicit help and no Annotated params."""

    @task
    def my_task(
        ctx: ToolkitContext,
        name: str,
        count: int = 5,
    ) -> None: ...

    # Should have empty or no help dict
    assert not my_task.help or my_task.help == {}  # type: ignore[attr-defined]


def test_task_decorator_aliases_preserved():
    """Test that task aliases and other options are preserved with help merging."""

    @task(aliases=["mt"], help={"name": "Custom help"})
    def my_task(
        ctx: ToolkitContext,
        name: Annotated[str, "Default help"],
    ) -> None: ...

    # Aliases should be preserved
    assert my_task.aliases == ["mt"]  # type: ignore[attr-defined]
    # Help should be merged correctly
    assert my_task.help["name"] == "Custom help"  # type: ignore[attr-defined]
