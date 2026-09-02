import os
import tty
from contextlib import closing

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
