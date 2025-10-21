import os

import pytest
from invoke.util import debug

from invoke_toolkit import Context, task
from invoke_toolkit.collections import ToolkitCollection
from invoke_toolkit.output import SecretScrubberConsole, get_console
from invoke_toolkit.program import ToolkitProgram


def test_console_object(monkeypatch):
    monkeypatch.setenv("SECRET", "12345")
    console = SecretScrubberConsole(secret_patterns=["*"], record=True)
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
        (["SUPER_SECRET"], ["--scrub-stdout"], ["SUPER_SECRET"], []),
        # only out
        (["SUPER_SECRET"], ["--scrub-stderr"], [], ["SUPER_SECRET"]),
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

    p = ToolkitProgram(namespace=ToolkitCollection(nothing))
    program_arguments = [""]
    for ptrn in pattern:
        program_arguments.extend(["--scrub-pattern", ptrn])

    program_arguments.extend(stream_args)
    program_arguments.append("nothing")

    debug(f"Running the program with {program_arguments=}")
    p.run(program_arguments, exit=False)
    out_console, err_console = get_console("out"), get_console("err")
    assert (
        out_console.secret_patterns == out_patterns
        and err_console.secret_patterns == err_patterns
    ), program_arguments


def test_console_scrubber(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    @task()
    def leaker(ctx: Context):
        ctx.print(f"{os.environ['SUPER_SECRET']}")

    monkeypatch.setenv("SUPER_SECRET", "dont_show")
    p = ToolkitProgram(namespace=ToolkitCollection(leaker))
    p.run(
        ["", "-d", "--scrub-stdout", "--scrub-pattern", "SUPER_SECRET", "leaker"],
        exit=False,
    )
    out, _err = capsys.readouterr()
    assert "dont_show" not in out
