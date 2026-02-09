"""Tests for completion with Enum and Literal choices."""

import subprocess
import sys
from enum import Enum
from textwrap import dedent

from invoke_toolkit import Context, task
from invoke_toolkit.collections import ToolkitCollection


class Color(str, Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class Size(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


def test_completion_enum_choices(suppress_stderr_logging):
    """Test that completion shows enum choices."""
    coll = ToolkitCollection()

    @task
    def paint(ctx: Context, color: Color = Color.RED) -> None:
        """Paint with a color."""

    coll.add_task(paint)  # type: ignore[arg-type]

    # Simulate completion by calling run with the completion arguments
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            dedent("""
                import sys
                sys.argv = ['intk', '--complete', '--', 'intk', 'paint', '--color']

                from invoke_toolkit.collections import ToolkitCollection
                from invoke_toolkit import Context, task
                from enum import Enum

                class Color(str, Enum):
                    RED = "red"
                    GREEN = "green"
                    BLUE = "blue"

                coll = ToolkitCollection()

                @task
                def paint(ctx: Context, color: Color = Color.RED) -> None:
                    pass

                coll.add_task(paint)  # type: ignore[arg-type]

                from invoke_toolkit.testing import TestingToolkitProgram
                p = TestingToolkitProgram(namespace=coll)
                try:
                    p.run(sys.argv)
                except SystemExit:
                    pass
            """),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    output = result.stdout
    assert "red" in output, f"Expected 'red' in completion output, got: {output}"
    assert "green" in output, f"Expected 'green' in completion output, got: {output}"
    assert "blue" in output, f"Expected 'blue' in completion output, got: {output}"


def test_completion_literal_choices(suppress_stderr_logging):
    """Test that completion shows literal choices."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            dedent("""
                import sys
                sys.argv = ['intk', '--complete', '--', 'intk', 'build', '--mode']

                from invoke_toolkit.collections import ToolkitCollection
                from invoke_toolkit import Context, task
                from typing import Literal

                coll = ToolkitCollection()

                @task
                def build(ctx: Context, mode: Literal["debug", "release"] = "debug") -> None:
                    pass

                coll.add_task(build)  # type: ignore[arg-type]

                from invoke_toolkit.testing import TestingToolkitProgram
                p = TestingToolkitProgram(namespace=coll)
                try:
                    p.run(sys.argv)
                except SystemExit:
                    pass
            """),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    output = result.stdout
    assert "debug" in output, f"Expected 'debug' in completion output, got: {output}"
    assert "release" in output, (
        f"Expected 'release' in completion output, got: {output}"
    )


def test_completion_multiple_enum_params(suppress_stderr_logging):
    """Test that completion works with multiple enum parameters."""
    # Test color completion
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            dedent("""
                import sys
                sys.argv = ['intk', '--complete', '--', 'intk', 'configure', '--color']

                from invoke_toolkit.collections import ToolkitCollection
                from invoke_toolkit import Context, task
                from enum import Enum

                class Color(str, Enum):
                    RED = "red"
                    GREEN = "green"
                    BLUE = "blue"

                class Size(str, Enum):
                    SMALL = "small"
                    MEDIUM = "medium"
                    LARGE = "large"

                coll = ToolkitCollection()

                @task
                def configure(
                    ctx: Context,
                    color: Color = Color.RED,
                    size: Size = Size.MEDIUM,
                ) -> None:
                    pass

                coll.add_task(configure)  # type: ignore[arg-type]

                from invoke_toolkit.testing import TestingToolkitProgram
                p = TestingToolkitProgram(namespace=coll)
                try:
                    p.run(sys.argv)
                except SystemExit:
                    pass
            """),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    output = result.stdout
    assert "red" in output, f"Expected 'red' in color completion, got: {output}"
    assert "green" in output, f"Expected 'green' in color completion, got: {output}"
    assert "blue" in output, f"Expected 'blue' in color completion, got: {output}"

    # Test size completion
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            dedent("""
                import sys
                sys.argv = ['intk', '--complete', '--', 'intk', 'configure', '--size']

                from invoke_toolkit.collections import ToolkitCollection
                from invoke_toolkit import Context, task
                from enum import Enum

                class Color(str, Enum):
                    RED = "red"
                    GREEN = "green"
                    BLUE = "blue"

                class Size(str, Enum):
                    SMALL = "small"
                    MEDIUM = "medium"
                    LARGE = "large"

                coll = ToolkitCollection()

                @task
                def configure(
                    ctx: Context,
                    color: Color = Color.RED,
                    size: Size = Size.MEDIUM,
                ) -> None:
                    pass

                coll.add_task(configure)  # type: ignore[arg-type]

                from invoke_toolkit.testing import TestingToolkitProgram
                p = TestingToolkitProgram(namespace=coll)
                try:
                    p.run(sys.argv)
                except SystemExit:
                    pass
            """),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    output = result.stdout
    assert "small" in output, f"Expected 'small' in size completion, got: {output}"
    assert "medium" in output, f"Expected 'medium' in size completion, got: {output}"
    assert "large" in output, f"Expected 'large' in size completion, got: {output}"


def test_completion_union_literal(suppress_stderr_logging):
    """Test that completion works with optional literal parameters (Union with None)."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            dedent("""
                import sys
                sys.argv = ['intk', '--complete', '--', 'intk', 'process', '--level']

                from invoke_toolkit.collections import ToolkitCollection
                from invoke_toolkit import Context, task
                from typing import Literal

                coll = ToolkitCollection()

                @task
                def process(ctx: Context, level: Literal["low", "high"] | None = None) -> None:
                    pass

                coll.add_task(process)  # type: ignore[arg-type]

                from invoke_toolkit.testing import TestingToolkitProgram
                p = TestingToolkitProgram(namespace=coll)
                try:
                    p.run(sys.argv)
                except SystemExit:
                    pass
            """),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    output = result.stdout
    assert "low" in output, f"Expected 'low' in union literal completion, got: {output}"
    assert "high" in output, (
        f"Expected 'high' in union literal completion, got: {output}"
    )
