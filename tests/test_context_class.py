from invoke_toolkit import task, Context
from invoke_toolkit.testing import TestingToolkitProgram
from invoke_toolkit.collections import ToolkitCollection
from invoke_toolkit.context import ToolkitContext


@task()
def task_test(c: Context):
    with c.status("Entering status"):
        c.print("hello")


def test_context_class(capsys):
    @task()
    def task_test(c: Context):
        with c.status("Entering status"):
            c.print("hello")

    p = TestingToolkitProgram(namespace=ToolkitCollection(task_test))
    p.run(["", "task-test"], exit=False)
    captured = capsys.readouterr()
    # TODO: capture status with custom console object
    out, _err = captured.out, captured.err
    assert out.strip() == "hello"


def test_context_class_pint_err(capsys):
    @task()
    def task_test(c: Context):
        with c.status("Entering status"):
            c.print_err("hello")

    p = TestingToolkitProgram(namespace=ToolkitCollection(task_test))
    p.run(["", "task-test"], exit=False)
    captured = capsys.readouterr()
    # TODO: capture status with custom console object
    out, err = captured.out, captured.err
    assert not out.strip()
    assert "hello" in err


def test_context_print(capsys, suppress_stderr_logging):
    @task()
    def task_test(c: Context):
        c.print("ls")

    p = TestingToolkitProgram(namespace=ToolkitCollection(task_test))
    p.run(["", "-e", "task-test"], exit=False)
    captured = capsys.readouterr()
    # TODO: capture status with custom console object
    out, err = captured.out, captured.err
    assert out.strip() == "ls"
    assert not err


def test_disable_status_flag(capsys):
    """Test that status can be disabled for debugging"""

    @task()
    def task_with_status(c: Context):
        with c.status("Processing..."):
            c.print("hello")

    # Create a custom config with disable_status set to True
    from invoke_toolkit.config import ToolkitConfig

    class DebugConfig(ToolkitConfig):
        extra_defaults = {"disable_status": True}

    from invoke_toolkit.program import ToolkitProgram

    p = ToolkitProgram(
        namespace=ToolkitCollection(task_with_status), config_class=DebugConfig
    )
    p.run(["", "task-with-status"], exit=False)
    captured = capsys.readouterr()
    out = captured.out
    # When status is disabled, no status spinner should be shown
    assert "hello" in out


def test_get_schema_with_defaults():
    """ctx.get_schema() returns defaults when config path doesn't exist."""
    from invoke_toolkit.config import config_schema, ConfigSchema, ToolkitConfig
    from invoke_toolkit.config.registry import clear_registry

    clear_registry()

    @config_schema("test")
    class TestConfig(ConfigSchema):
        value: str = "default"

    ctx = ToolkitContext(config=ToolkitConfig())
    config = ctx.get_schema(TestConfig)

    assert config.value == "default"

    clear_registry()
