import io
import logging
import shlex
import sys
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from invoke.util import debug
from rich.console import Console

from invoke_toolkit import Context, task
from invoke_toolkit.collections import ToolkitCollection
from invoke_toolkit.config import ToolkitConfig
from invoke_toolkit.config.status_helper import StatusHelper
from invoke_toolkit.output import SecretRedactorConsole, get_console
from invoke_toolkit.testing import TestingToolkitProgram
from invoke_toolkit.runners.rich import RedactingStream


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


@pytest.mark.parametrize("split", range(1, len("synthetic-secret")))
def test_redacting_stream_keeps_secret_prefix_across_flushes(monkeypatch, split):
    monkeypatch.setenv("STREAM_SECRET", "synthetic-secret")
    console = SecretRedactorConsole(secret_patterns=["^STREAM_SECRET$"])
    output = io.StringIO()
    stream = RedactingStream(console, output)

    stream.write("prompt> ")
    stream.flush()
    assert output.getvalue() == "prompt> "
    assert stream.write("synthetic-secret"[:split]) == split
    stream.flush()
    assert output.getvalue() == "prompt> "
    stream.write("synthetic-secret"[split:] + "!\n")
    stream.flush()
    assert output.getvalue() == "prompt> $STREAM_SECRET!\n"


@pytest.mark.parametrize(
    "substitution, expected", [("${}", "$LONG!"), ("*", "******!")]
)
def test_redacting_stream_preserves_longest_secret_precedence(
    monkeypatch, substitution, expected
):
    monkeypatch.setenv("SHORT", "abc")
    monkeypatch.setenv("LONG", "abcdef")
    console = SecretRedactorConsole(
        secret_patterns=["^(SHORT|LONG)$"], substitution=substitution
    )
    output = io.StringIO()
    stream = RedactingStream(console, output)
    stream.write("abc")
    stream.flush()
    assert output.getvalue() == ""
    stream.write("def!")
    stream.flush()
    assert output.getvalue() == expected


def test_secret_initialization_never_logs_values(monkeypatch, caplog):
    monkeypatch.setenv("LOG_SECRET", "synthetic-log-secret")
    with caplog.at_level(logging.DEBUG, logger="invoke"):
        console = SecretRedactorConsole(secret_patterns=["^LOG_SECRET$"])
        console.secret_patterns = ["^LOG_SECRET$"]
    assert "synthetic-log-secret" not in caplog.text


@pytest.fixture
def redacting_ctx():
    return Context(ToolkitConfig(overrides={"run": {"in_stream": False}}))


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("stream_name", ["out", "err"])
def test_redacting_runner_drains_nonsecret_prefix_at_eof(
    redacting_ctx, monkeypatch, asynchronous, stream_name
):
    monkeypatch.setenv("STREAM_SECRET", "synthetic-secret")
    get_console(stream_name).secret_patterns = ["^STREAM_SECRET$"]
    output = io.StringIO()
    child = f"import sys; sys.std{stream_name}.write('synthetic-')"
    result = redacting_ctx.run(
        shlex.join([sys.executable, "-c", child]),
        asynchronous=asynchronous,
        **{f"{stream_name}_stream": output},
    )
    if asynchronous:
        result = result.join()
    assert result.exited == 0
    assert output.getvalue() == "synthetic-"


def test_redacting_stream_uses_global_longest_first_replacements(monkeypatch):
    monkeypatch.setenv("SHORT", "abc")
    monkeypatch.setenv("LONG", "bcdef")
    console = SecretRedactorConsole(secret_patterns=["^(SHORT|LONG)$"])
    output = io.StringIO()
    stream = RedactingStream(console, output)
    for character in "abcdef!":
        stream.write(character)
        stream.flush()
    assert output.getvalue() == "a$LONG!"


@pytest.mark.parametrize("stream_name", ["out", "err"])
def test_verbose_status_renders_redacted_output(
    redacting_ctx, monkeypatch, stream_name
):
    monkeypatch.setenv("STREAM_SECRET", "synthetic-secret")
    get_console(stream_name).secret_patterns = ["^STREAM_SECRET$"]
    output = io.StringIO()
    helper = StatusHelper(
        Console(file=output, force_terminal=True, width=100), show_command_output=True
    )
    redacting_ctx._set("_status_helper", helper)
    with redacting_ctx.status("working") as status:
        redacting_ctx.run(
            shlex.join(
                [
                    sys.executable,
                    "-c",
                    f"import sys; sys.std{stream_name}.write('synthetic-secret')",
                ]
            )
        )
    Console(file=output).print(status._build_renderable())
    assert "synthetic-secret" not in output.getvalue()
    assert "$STREAM_SECRET" in output.getvalue()


def test_redacting_stream_drains_mismatched_prefix_and_repeated_unicode_secrets(
    monkeypatch,
):
    monkeypatch.setenv("UNICODE_SECRET", "é秘密")
    console = SecretRedactorConsole(secret_patterns=["^UNICODE_SECRET$"])
    output = io.StringIO()
    stream = RedactingStream(console, output)
    for chunk in ("é", "X ", "é", "秘", "密é秘", "密\né"):
        stream.write(chunk)
        stream.flush()
    assert output.getvalue() == "éX $UNICODE_SECRET$UNICODE_SECRET\n"
    stream.finish()
    assert output.getvalue() == "éX $UNICODE_SECRET$UNICODE_SECRET\né"


def test_redacting_runner_finishes_output_before_command_failure(
    redacting_ctx, monkeypatch
):
    monkeypatch.setenv("STREAM_SECRET", "synthetic-secret")
    get_console("out").secret_patterns = ["^STREAM_SECRET$"]
    output = io.StringIO()
    from invoke import UnexpectedExit

    with pytest.raises(UnexpectedExit):
        redacting_ctx.run(
            shlex.join(
                [
                    sys.executable,
                    "-c",
                    "import sys; sys.stdout.write('synthetic-'); sys.exit(1)",
                ]
            ),
            out_stream=output,
        )
    assert output.getvalue() == "synthetic-"


def test_redacting_stream_serializes_writes_and_emission(monkeypatch):
    monkeypatch.setenv("STREAM_SECRET", "synthetic-secret")
    console = SecretRedactorConsole(secret_patterns=["^STREAM_SECRET$"])
    entered = Event()
    release = Event()

    class PausingOutput(io.StringIO):
        def write(self, text):
            if text == "first!":
                entered.set()
                assert release.wait(5)
            return super().write(text)

    output = PausingOutput()
    stream = RedactingStream(console, output)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(stream.write, "first!")
        assert entered.wait(5)
        second_started = Event()

        def second_write():
            second_started.set()
            stream.write("second!")

        second = executor.submit(second_write)
        assert second_started.wait(5)
        try:
            assert not second.done()
        finally:
            release.set()
        first.result(timeout=5)
        second.result(timeout=5)
    stream.finish()
    assert output.getvalue() == "first!second!"


def test_redacting_runner_keeps_prefix_until_stdin_echo_finishes(monkeypatch):
    from invoke_toolkit.runners.rich import NoStdoutRunner

    monkeypatch.setenv("STREAM_SECRET", "synthetic-secret")
    get_console("out").secret_patterns = ["^STREAM_SECRET$"]
    stdout_ended = Event()

    class EOFSignalingRunner(NoStdoutRunner):
        def handle_stdout(self, buffer_, hide, output):
            try:
                super().handle_stdout(buffer_, hide, output)
            finally:
                stdout_ended.set()

    class DelayedInput(io.StringIO):
        def read(self, size=-1):
            assert stdout_ended.wait(5)
            return super().read(size)

    ctx = Context(ToolkitConfig(overrides={"runners": {"local": EOFSignalingRunner}}))
    output = io.StringIO()
    ctx.run(
        shlex.join(
            [
                sys.executable,
                "-c",
                "import os,sys; os.write(1, b'synthetic-'); os.close(1); sys.stdin.read(6)",
            ]
        ),
        in_stream=DelayedInput("secret"),
        echo_stdin=True,
        out_stream=output,
    )
    assert output.getvalue() == "$STREAM_SECRET"


# Fix test isolation issues by simplifying stderr-checking tests
