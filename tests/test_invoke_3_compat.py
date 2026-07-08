"""
Tests for invoke 3.0.x compatibility.

invoke 3.0 introduced two related breaking changes that affect invoke-toolkit:

1. ``Call.make_context`` now requires a second argument ``core_parse_result``
   (a ``ParseResult`` instance) so that ``Context.remainder`` can be populated
   from the CLI parser's remainder value (text after a standalone ``--``).

2. ``Context.__init__`` now accepts a ``remainder`` keyword argument and stores
   it as ``self.remainder``.

These tests verify that:
- ``ToolkitCall.make_context`` accepts ``core_parse_result`` and propagates
  ``remainder`` into the resulting ``ToolkitContext``.
- ``ToolkitContext`` exposes ``ctx.remainder`` correctly.
- ``ToolkitExecutor`` never passes ``None`` as ``core_parse_result`` (it
  defaults to an empty ``ParseResult()``).
- End-to-end: a task can read ``ctx.remainder`` when invoked with ``-- extra``.
"""

from invoke.parser import ParseResult
from invoke.tasks import Task

from invoke_toolkit import Context, task
from invoke_toolkit.collections import ToolkitCollection
from invoke_toolkit.config import ToolkitConfig
from invoke_toolkit.context.context import ToolkitContext
from invoke_toolkit.executor import ToolkitExecutor
from invoke_toolkit.tasks.tasks import ToolkitCall


# ---------------------------------------------------------------------------
# Unit: ToolkitCall.make_context
# ---------------------------------------------------------------------------


def _dummy_task_func(ctx: Context) -> None:  # pragma: no cover
    """Minimal real task used as a ToolkitCall target in unit tests."""


_DUMMY_TASK: Task = task(_dummy_task_func)  # type: ignore[assignment]


def _make_parse_result(remainder: str = "") -> ParseResult:
    """Return a ParseResult whose .remainder is set to *remainder*."""
    pr = ParseResult()
    pr.remainder = remainder
    return pr


def test_make_context_without_core_parse_result():
    """make_context(config) with no core_parse_result → remainder defaults to ''."""
    config = ToolkitConfig()
    c = ToolkitCall(_DUMMY_TASK)
    ctx = c.make_context(config)
    assert isinstance(ctx, ToolkitContext)
    assert ctx.remainder == ""


def test_make_context_with_empty_parse_result():
    """make_context(config, core_parse_result=ParseResult()) → remainder is ''."""
    config = ToolkitConfig()
    c = ToolkitCall(_DUMMY_TASK)
    ctx = c.make_context(config, core_parse_result=_make_parse_result(""))
    assert isinstance(ctx, ToolkitContext)
    assert ctx.remainder == ""


def test_make_context_propagates_remainder():
    """make_context passes ParseResult.remainder into ToolkitContext.remainder."""
    config = ToolkitConfig()
    c = ToolkitCall(_DUMMY_TASK)
    ctx = c.make_context(config, core_parse_result=_make_parse_result("extra args"))
    assert ctx.remainder == "extra args"


def test_make_context_with_none_core_parse_result():
    """Passing core_parse_result=None explicitly is safe (backward compat)."""
    config = ToolkitConfig()
    c = ToolkitCall(_DUMMY_TASK)
    ctx = c.make_context(config, core_parse_result=None)
    assert ctx.remainder == ""


# ---------------------------------------------------------------------------
# Unit: ToolkitContext.__init__
# ---------------------------------------------------------------------------


def test_toolkit_context_remainder_default():
    """ToolkitContext() has remainder='' by default."""
    ctx = ToolkitContext()
    assert ctx.remainder == ""


def test_toolkit_context_remainder_kwarg():
    """ToolkitContext(remainder=...) stores the value on the instance."""
    ctx = ToolkitContext(remainder="docker run --rm alpine")
    assert ctx.remainder == "docker run --rm alpine"


def test_toolkit_context_remainder_with_config():
    """ToolkitContext(config=..., remainder=...) works with both args."""
    config = ToolkitConfig()
    ctx = ToolkitContext(config=config, remainder="--verbose")
    assert ctx.remainder == "--verbose"


# ---------------------------------------------------------------------------
# Unit: ToolkitExecutor.__init__
# ---------------------------------------------------------------------------


def test_executor_core_defaults_to_parse_result():
    """ToolkitExecutor.core is never None; defaults to ParseResult()."""
    col = ToolkitCollection()
    executor = ToolkitExecutor(collection=col)
    assert executor.core is not None
    assert isinstance(executor.core, ParseResult)


def test_executor_core_accepts_explicit_parse_result():
    """ToolkitExecutor.core stores an explicitly provided ParseResult."""
    col = ToolkitCollection()
    pr = _make_parse_result("some remainder")
    executor = ToolkitExecutor(collection=col, core=pr)
    assert executor.core is pr
    assert executor.core.remainder == "some remainder"


def test_executor_core_none_becomes_empty_parse_result():
    """Passing core=None explicitly still yields a ParseResult(), not None."""
    col = ToolkitCollection()
    executor = ToolkitExecutor(collection=col, core=None)
    assert executor.core is not None
    assert isinstance(executor.core, ParseResult)
    assert executor.core.remainder == ""


# ---------------------------------------------------------------------------
# Integration: ctx.remainder is accessible inside a task
# ---------------------------------------------------------------------------


def test_task_receives_remainder_via_context():
    """A task can read ctx.remainder when the program is given a remainder."""
    captured: list[str] = []

    ns = ToolkitCollection()

    @task  # type: ignore[arg-type]
    def wrapper_task(ctx: Context):
        """Wrapper task that captures ctx.remainder."""
        captured.append(ctx.remainder)

    ns.add_task(wrapper_task)  # type: ignore[arg-type]

    pr = _make_parse_result("echo hello world")
    config = ToolkitConfig()
    executor = ToolkitExecutor(collection=ns, config=config, core=pr)
    executor.execute("wrapper-task")

    assert len(captured) == 1
    assert captured[0] == "echo hello world"


def test_task_remainder_empty_when_not_provided():
    """ctx.remainder is '' when no remainder was parsed."""
    captured: list[str] = []

    ns = ToolkitCollection()

    @task  # type: ignore[arg-type]
    def simple_task(ctx: Context):
        """Simple task that captures ctx.remainder."""
        captured.append(ctx.remainder)

    ns.add_task(simple_task)  # type: ignore[arg-type]

    executor = ToolkitExecutor(collection=ns)
    executor.execute("simple-task")

    assert captured == [""]
