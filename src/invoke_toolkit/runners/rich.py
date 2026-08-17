"""
Config object used for invoke attribute resolution
in tasks.
"""

import sys
from typing import TYPE_CHECKING

from invoke.runners import Local
from invoke.util import debug
from rich.syntax import Syntax

from invoke_toolkit.output import get_console

if TYPE_CHECKING:
    from invoke_toolkit.config.status_helper import StatusHelper


class RedactingStream:
    """A file-like wrapper that redacts secrets before writing output."""

    def __init__(self, console, original_stream):
        """
        Initialize the redacting stream.

        Args:
            console: The SecretRedactorConsole to use for redaction
            original_stream: The original stream to write to
        """
        self.console = console
        self.original_stream = original_stream
        self.encoding = getattr(original_stream, "encoding", "utf-8") or "utf-8"

    def write(self, text: str) -> int:
        """Write text after redacting secrets."""
        if not text:
            return 0

        redacted_text = self.console.redact(text)
        return self.original_stream.write(redacted_text)

    def flush(self) -> None:
        """Flush the underlying stream."""
        if hasattr(self.original_stream, "flush"):
            self.original_stream.flush()

    def isatty(self) -> bool:
        """Return whether the stream is a tty."""
        if hasattr(self.original_stream, "isatty"):
            return self.original_stream.isatty()
        return False

    def __getattr__(self, name):
        """Delegate other attributes to the original stream."""
        return getattr(self.original_stream, name)


class OutputCapturingStream:
    """A file-like wrapper that captures output lines and feeds them to a StatusHelper."""

    def __init__(self, status_helper: "StatusHelper", original_stream):
        self._status_helper = status_helper
        self.original_stream = original_stream
        self.encoding = getattr(original_stream, "encoding", "utf-8") or "utf-8"
        self._buffer = ""

    def write(self, text: str) -> int:
        """Write text, splitting into lines for capture."""
        if not text:
            return 0

        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._status_helper.capture_line(line)

        return len(text)

    def flush(self) -> None:
        """Flush remaining buffer content."""
        if self._buffer:
            self._status_helper.capture_line(self._buffer)
            self._buffer = ""
        if hasattr(self.original_stream, "flush"):
            self.original_stream.flush()

    def isatty(self) -> bool:
        """Return whether the underlying stream is a tty."""
        if hasattr(self.original_stream, "isatty"):
            return self.original_stream.isatty()
        return False

    def __getattr__(self, name):
        """Delegate other attributes to the original stream."""
        return getattr(self.original_stream, name)


class NoStdoutRunner(Local):
    """Invoke runner that prints to stderr when invoke is used with -e/--echo
    and redacts secrets from subprocess output when redaction is enabled.
    """

    def echo(self, command):
        if hasattr(self.context, "print"):
            # Safety first
            syn = Syntax(command, "bash")
            self.context.print(syn)
        else:
            debug("context is missing print")
            print(self.opts["echo_format"].format(command=command), file=sys.stderr)

    def _get_status_helper(self) -> "StatusHelper | None":
        if hasattr(self.context, "_status_helper"):
            return self.context._status_helper  # pylint: disable=protected-access
        return None

    def run(self, command, **kwargs):
        """Execute command with redacting streams and optional output capture."""
        # Get the configured console objects
        out_console = get_console("out")
        err_console = get_console("err")

        # Check if redaction is enabled on any stream
        has_out_redaction = bool(out_console.secret_patterns)
        has_err_redaction = bool(err_console.secret_patterns)

        # If redaction is enabled, wrap the streams
        if has_out_redaction or has_err_redaction:
            # Get the output streams from kwargs or use defaults
            out_stream = kwargs.get("out_stream") or sys.stdout
            err_stream = kwargs.get("err_stream") or sys.stderr

            # Wrap streams with redacting wrappers
            if has_out_redaction:
                kwargs["out_stream"] = RedactingStream(out_console, out_stream)

            if has_err_redaction:
                kwargs["err_stream"] = RedactingStream(err_console, err_stream)

            debug(
                f"Running with redacting streams: {has_out_redaction=}, {has_err_redaction=}"
            )

        # If we're inside a verbose status, capture output for the panel
        status_helper = self._get_status_helper()
        if status_helper and status_helper.is_verbose:
            out_stream = kwargs.get("out_stream") or sys.stdout
            err_stream = kwargs.get("err_stream") or sys.stderr
            kwargs["out_stream"] = OutputCapturingStream(status_helper, out_stream)
            kwargs["err_stream"] = OutputCapturingStream(status_helper, err_stream)
            # Disable hide so output flows through our capturing stream
            # (the stream feeds the Live panel instead of printing to terminal)
            kwargs["hide"] = False

        return super().run(command, **kwargs)
