"""Tests for completion with Enum and Literal choices and custom callbacks."""

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


def test_completion_callback_basic(suppress_stderr_logging):
    """Test that completion callbacks are invoked and return choices."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            dedent("""
                import sys
                sys.argv = ['intk', '--complete', '--', 'intk', 'deploy', '--branch']

                from typing import Annotated
                from invoke_toolkit.collections import ToolkitCollection
                from invoke_toolkit import Context, task

                def complete_branches(ctx: Context, incomplete: str = "") -> list[str]:
                    branches = ["main", "develop", "feature/new-api"]
                    return [b for b in branches if b.startswith(incomplete)]

                coll = ToolkitCollection()

                @task
                def deploy(
                    ctx: Context,
                    branch: Annotated[str, "Git branch to deploy", complete_branches]
                ) -> None:
                    pass

                coll.add_task(deploy)  # type: ignore[arg-type]

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
    assert "main" in output, f"Expected 'main' in callback completion, got: {output}"
    assert "develop" in output, (
        f"Expected 'develop' in callback completion, got: {output}"
    )
    assert "feature/new-api" in output, (
        f"Expected 'feature/new-api' in callback completion, got: {output}"
    )


def test_completion_callback_with_filtering(suppress_stderr_logging):
    """Test that completion callbacks filter results based on incomplete value."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            dedent("""
                import sys
                sys.argv = ['intk', '--complete', '--', 'intk', 'deploy', '--branch']

                from typing import Annotated
                from invoke_toolkit.collections import ToolkitCollection
                from invoke_toolkit import Context, task

                def complete_branches(ctx: Context, incomplete: str = "") -> list[str]:
                    branches = ["main", "develop", "feature/new-api", "feature/another"]
                    return [b for b in branches if b.startswith(incomplete)]

                coll = ToolkitCollection()

                @task
                def deploy(
                    ctx: Context,
                    branch: Annotated[str, "Git branch to deploy", complete_branches]
                ) -> None:
                    pass

                coll.add_task(deploy)  # type: ignore[arg-type]

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
    # All branches should be returned since no incomplete prefix was provided
    assert "main" in output, f"Expected 'main' in completion, got: {output}"
    assert "develop" in output, f"Expected 'develop' in completion, got: {output}"


def test_completion_callback_priority_over_enum(suppress_stderr_logging):
    """Test that completion callback has higher priority than enum."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            dedent("""
                import sys
                sys.argv = ['intk', '--complete', '--', 'intk', 'deploy', '--env']

                from typing import Annotated
                from enum import Enum
                from invoke_toolkit.collections import ToolkitCollection
                from invoke_toolkit import Context, task

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
                    env: Annotated[Environment, "Deployment environment", complete_env]
                ) -> None:
                    pass

                coll.add_task(deploy)  # type: ignore[arg-type]

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
    # Should use callback results, not enum values
    assert "development" in output, (
        f"Expected callback result 'development' in completion, got: {output}"
    )
    assert "staging" in output, (
        f"Expected callback result 'staging' in completion, got: {output}"
    )
    assert "production" in output, (
        f"Expected callback result 'production' in completion, got: {output}"
    )
