import os
import sys
import termios
import textwrap
import tty
from contextlib import closing

import pexpect

import pytest

from invoke_toolkit import Context
from invoke_toolkit.runners.rich import NoStdoutRunner


@pytest.mark.skipif(os.name == "nt", reason="PTYs are POSIX-only")
def test_read_our_stdin_handles_escape_sequence_from_pty():
    master_fd, slave_fd = os.openpty()
    try:
        tty.setcbreak(slave_fd)
        os.write(master_fd, b"\x1b[A")
        stream = os.fdopen(slave_fd, "rb", closefd=False)
        with closing(stream):
            runner = NoStdoutRunner(Context())
            runner.encoding = "utf-8"
            assert runner.read_our_stdin(stream) == "\x1b[A"
    finally:
        os.close(master_fd)
        os.close(slave_fd)


@pytest.mark.skipif(os.name == "nt", reason="PTYs are POSIX-only")
def test_pty_run_forwards_enter_as_carriage_return(tmp_path):
    child = tmp_path / "read_enter.py"
    child.write_text(
        textwrap.dedent(
            """
            import os
            import sys
            import tty

            tty.setraw(sys.stdin.fileno())
            os.write(sys.stdout.fileno(), b"READY\\n")
            os.read(sys.stdin.fileno(), 1)
            os.write(sys.stdout.fileno(), b"ARMED\\n")
            byte = os.read(sys.stdin.fileno(), 1)
            os.write(sys.stdout.fileno(), b"BYTE:" + byte.hex().encode() + b"\\n")
            """
        ),
        encoding="utf-8",
    )
    parent = tmp_path / "run_child.py"
    parent.write_text(
        textwrap.dedent(
            f"""
            import shlex
            import sys

            from invoke_toolkit import Config, Context

            command = shlex.join([sys.executable, {str(child)!r}])

            Context(config=Config()).run(
                command,
                pty=True,
                echo_stdin=False,
            )
            """
        ),
        encoding="utf-8",
    )
    process = pexpect.spawn(sys.executable, [str(parent)], encoding=None, timeout=5)
    original_settings = termios.tcgetattr(process.child_fd)
    assert original_settings[0] & termios.ICRNL
    try:
        process.expect(b"READY")
        assert process.waitnoecho(timeout=process.timeout)
        process.send(b"!")
        process.expect(b"ARMED")
        process.send(b"\r")
        process.expect(b"BYTE:0d")
        process.expect(pexpect.EOF)
        assert termios.tcgetattr(process.child_fd) == original_settings
    finally:
        process.close(force=True)
