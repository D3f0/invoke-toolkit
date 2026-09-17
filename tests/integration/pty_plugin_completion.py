"""Exercise plugin completion through Bash and a real pseudo-terminal."""

from __future__ import annotations

import os
import sys
from typing import Any

import pexpect

PROMPT = "INTK-PTY> "
TIMEOUT = 15


def complete(child: Any, command: str, expected: str) -> None:
    """Type a partial command, press Tab, and require the expected completion."""
    child.send(command)
    child.send("\t")
    child.expect_exact(expected, timeout=TIMEOUT)
    child.sendcontrol("c")
    child.expect_exact(PROMPT, timeout=TIMEOUT)


def main() -> None:
    child = pexpect.spawn(
        "/bin/bash",
        ["--noprofile", "--norc"],
        encoding="utf-8",
        timeout=TIMEOUT,
        env={**os.environ, "PS1": PROMPT},
    )
    child.logfile = sys.stdout
    try:
        child.expect_exact(PROMPT, timeout=TIMEOUT)
        child.sendline("source <(intk --print-completion-script bash)")
        child.expect_exact(PROMPT, timeout=TIMEOUT)
        complete(
            child,
            "intk -x plugin.remove --name fixture-sta",
            "fixture-static-plugin",
        )
        complete(
            child,
            "intk -x plugin.update --name fixture-lin",
            "fixture-linked-plugin",
        )
    finally:
        child.close(force=True)
    if child.isalive():
        raise RuntimeError("Bash PTY did not terminate")


if __name__ == "__main__":
    main()
