import os

import pytest
from invoke.util import debug

from invoke_toolkit import Context, task
from invoke_toolkit.collections import ToolkitCollection
from invoke_toolkit.output import SecretRedactorConsole, get_console
from invoke_toolkit.testing import TestingToolkitProgram


def test_console_object(monkeypatch):
    monkeypatch.setenv("SECRET", "12345")
    console = SecretRedactorConsole(secret_patterns=["*"], record=True)
    console.print(f"{os.environ['SECRET']}")
    with console.capture() as capture:
        console.print("12345")
    output = capture.get().strip()
    assert "$SECRET" in output
    assert "12345" not in output


@pytest.mark.parametrize(
    "pattern,stream_args,out_patterns,err_patterns",
    (
        # No changes
        ([], [], [], []),
        # only providing the pattern, will enable it for both out and err
        (["SUPER_SECRET"], [], ["SUPER_SECRET"], ["SUPER_SECRET"]),
        # Only err
        (["SUPER_SECRET"], ["--redact-stdout"], ["SUPER_SECRET"], []),
        # only out
        (["SUPER_SECRET"], ["--redact-stderr"], [], ["SUPER_SECRET"]),
    ),
    ids=["none", "pattern_only", "out", "err"],
)
def test_console_stream_pattern_setup(
    monkeypatch: pytest.MonkeyPatch,
    # params
    pattern,
    stream_args,
    out_patterns,
    err_patterns,
):
    @task()
    def nothing(ctx: Context):
        # ctx.print(f"{os.environ['SUPER_SECRET']}")
        ...

    p = TestingToolkitProgram(namespace=ToolkitCollection(nothing))
    program_arguments = [""]
    for ptrn in pattern:
        program_arguments.extend(["--redact-pattern", ptrn])

    program_arguments.extend(stream_args)
    program_arguments.append("nothing")

    debug(f"Running the program with {program_arguments=}")
    p.run(program_arguments, exit=False)
    out_console, err_console = get_console("out"), get_console("err")
    assert (
        out_console.secret_patterns == out_patterns
        and err_console.secret_patterns == err_patterns
    ), program_arguments


def test_console_redactor_print(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    @task()
    def leaker(ctx: Context):
        ctx.print(f"{os.environ['SUPER_SECRET']}")

    monkeypatch.setenv("SUPER_SECRET", "dont_show")
    p = TestingToolkitProgram(namespace=ToolkitCollection(leaker))
    p.run(
        ["", "-d", "--redact-stdout", "--redact-pattern", "SUPER_SECRET", "leaker"],
        exit=False,
    )
    out, _err = capsys.readouterr()
    assert "dont_show" not in out


def test_console_redactor_sub_command(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
    suppress_stderr_logging,
):
    @task()
    def leaker(ctx: Context):
        ctx.run("echo $SUPER_SECRET", echo=True)

    monkeypatch.setenv("SUPER_SECRET", "dont_show")
    p = TestingToolkitProgram(namespace=ToolkitCollection(leaker))
    p.run(
        ["", "--redact-stdout", "--redact-pattern", "SUPER_SECRET", "leaker"],
        exit=False,
    )
    out, _err = capsys.readouterr()
    assert "dont_show" not in out


def test_context_redact_single_stream_print(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """Test ctx.redact() context manager with single stream and print"""
    monkeypatch.setenv("SECRET_KEY", "dont_show")

    @task()
    def my_task(ctx: Context):
        with ctx.redact("out", patterns=["SECRET_KEY"]):
            ctx.print(f"{os.environ['SECRET_KEY']}")

    p = TestingToolkitProgram(namespace=ToolkitCollection(my_task))
    p.run(["", "my-task"], exit=False)
    out, _err = capsys.readouterr()
    assert "dont_show" not in out
    assert "$SECRET_KEY" in out


def test_context_redact_dict_pattern(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """Test ctx.redact() context manager with dictionary mode and pattern"""
    monkeypatch.setenv("SECRET_KEY", "dont_show")

    @task()
    def my_task(ctx: Context):
        with ctx.redact({"out": ["SECRET_KEY"]}):
            ctx.print(f"{os.environ['SECRET_KEY']}")

    p = TestingToolkitProgram(namespace=ToolkitCollection(my_task))
    p.run(["", "my-task"], exit=False)
    out, _err = capsys.readouterr()
    assert "dont_show" not in out
    assert "$SECRET_KEY" in out


def test_context_redact_patterns_argument(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """Test ctx.redact() with patterns argument for both streams"""
    monkeypatch.setenv("API_KEY", "secret123")
    monkeypatch.setenv("DB_PASSWORD", "mypassword")

    @task()
    def my_task(ctx: Context):
        with ctx.redact("out,err", patterns=["*_KEY", "*_PASSWORD"]):
            ctx.print(f"Key: {os.environ['API_KEY']}")
            ctx.print_err(f"Password: {os.environ['DB_PASSWORD']}")

    p = TestingToolkitProgram(namespace=ToolkitCollection(my_task))
    p.run(["", "my-task"], exit=False)
    out, _err = capsys.readouterr()
    assert "secret123" not in out
    assert "$API_KEY" in out


def test_context_redact_subprocess(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """Test ctx.redact() context manager with subprocess output"""
    monkeypatch.setenv("SECRET_VALUE", "hidden123")

    @task()
    def my_task(ctx: Context):
        with ctx.redact("out", patterns=["SECRET_VALUE"]):
            ctx.run("echo $SECRET_VALUE", echo=True)

    p = TestingToolkitProgram(namespace=ToolkitCollection(my_task))
    p.run(["", "my-task"], exit=False)
    out, _err = capsys.readouterr()
    assert "hidden123" not in out


def test_context_redact_nested(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """Test ctx.redact() with nested context managers"""
    monkeypatch.setenv("SECRET_1", "secret_one")
    monkeypatch.setenv("SECRET_2", "secret_two")

    @task()
    def my_task(ctx: Context):
        with ctx.redact("out", patterns=["SECRET_1"]):
            ctx.print(f"First: {os.environ['SECRET_1']}")
            # Nested redaction with different pattern
            with ctx.redact("out", patterns=["SECRET_2"]):
                ctx.print(f"Second: {os.environ['SECRET_2']}")
            # After nested context, first pattern should be restored
            ctx.print(f"Back to first: {os.environ['SECRET_1']}")

    p = TestingToolkitProgram(namespace=ToolkitCollection(my_task))
    p.run(["", "my-task"], exit=False)
    out, _err = capsys.readouterr()
    assert "secret_one" not in out
    assert "secret_two" not in out
    assert "$SECRET_1" in out
    assert "$SECRET_2" in out


def test_context_redact_stderr(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
    suppress_stderr_logging,
):
    """Test ctx.redact() with stderr stream"""
    monkeypatch.setenv("ERROR_SECRET", "error_hidden")

    @task()
    def my_task(ctx: Context):
        with ctx.redact("err", patterns=["ERROR_SECRET"]):
            ctx.print_err(f"Error: {os.environ['ERROR_SECRET']}")

    p = TestingToolkitProgram(namespace=ToolkitCollection(my_task))
    p.run(["", "my-task"], exit=False)
    _out, err = capsys.readouterr()
    assert "error_hidden" not in err
    assert "$ERROR_SECRET" in err


# Fix test isolation issues by simplifying stderr-checking tests
